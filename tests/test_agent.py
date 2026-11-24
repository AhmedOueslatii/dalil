"""Tests de la boucle de l'agent avec un LLM scripté : aucun appel réseau ni base."""
from decimal import Decimal

from app.agent.llm import AssistantTurn, ToolCall, ToolResult, ToolResults, ToolSpec, UserMessage, to_gemini_contents
from app.agent.loop import MAX_LLM_CALLS, run_agent
from app.agent.tools import ASK_USER_TOOL, Tool, ToolOutput, amounts_in, compute_wealth_tax, search_texts
from app.guardrails import DONT_KNOW

ART_88 = {
    "article": "Art. 88",
    "titre": "Loi de finances 2026",
    "source": "Loi2025_17-1.pdf",
    "texte": "0,5% de la fortune dont la valeur varie de 3 millions de dinars à 5 millions de dinars.",
}


class ScriptedLLM:
    """Renvoie les tours prévus dans l'ordre et garde une copie de ce qu'il a reçu."""

    def __init__(self, turns):
        self.turns = list(turns)
        self.received = []

    def complete(self, system, messages, tools):
        self.received.append(list(messages))
        turn = self.turns.pop(0) if self.turns else self.turns_default()
        return turn

    def turns_default(self):
        return AssistantTurn(text="", tool_calls=[ToolCall("rechercher_textes", {"requete": f"q{len(self.received)}"})], tokens_in=10)


def fake_search(args, question):
    return ToolOutput({"passages": [ART_88]}, passages=[ART_88])


def tools(search=fake_search):
    spec = ToolSpec("rechercher_textes", "recherche", {"type": "object", "properties": {"requete": {"type": "string"}}})
    ask = ToolSpec(ASK_USER_TOOL, "précisions", {"type": "object", "properties": {}})
    return [Tool(spec, search), Tool(ask, lambda a, q: ToolOutput({}))]


def call(name="rechercher_textes", **args):
    return AssistantTurn(text="", tool_calls=[ToolCall(name, args)], tokens_in=100, tokens_out=10)


def answer(text):
    return AssistantTurn(text=text, tokens_in=200, tokens_out=50)


def test_search_then_cited_answer():
    llm = ScriptedLLM([
        call(requete="impôt sur la fortune"),
        answer("Le taux est de 0,5% entre 3 millions et 5 millions de dinars [Art. 88]."),
    ])
    result = run_agent("Quel est le taux de l'impôt sur la fortune ?", adapter=llm, tools=tools())

    assert result["statut"] == "reponse"
    assert "[Art. 88]" in result["reponse"]
    assert result["appels_llm"] == 2
    assert (result["tokens_in"], result["tokens_out"]) == (300, 60)
    assert [s["article"] for s in result["sources"]] == ["Art. 88"]
    assert [step["type"] for step in result["trace"]] == ["llm", "outil", "llm"]


def test_citation_outside_tool_results_falls_back_to_dont_know():
    llm = ScriptedLLM([call(requete="fortune"), answer("Le taux est de 2% [Art. 12].")])
    result = run_agent("Taux ?", adapter=llm, tools=tools())

    assert result["reponse"] == DONT_KNOW
    assert result["guardrail"]["fallback_dont_know"] is True


def test_invented_number_is_removed():
    llm = ScriptedLLM([
        call(requete="fortune"),
        answer("Le taux est de 0,5% [Art. 88]. Le seuil sera porté à 7 millions [Art. 88]."),
    ])
    result = run_agent("Taux ?", adapter=llm, tools=tools())

    assert "0,5%" in result["reponse"]
    assert "7 millions" not in result["reponse"]


def test_budget_stops_a_looping_model():
    llm = ScriptedLLM([])  # cherche indéfiniment
    result = run_agent("Taux ?", adapter=llm, tools=tools())

    assert result["statut"] == "budget_epuise"
    assert result["reponse"] == DONT_KNOW
    assert result["appels_llm"] == MAX_LLM_CALLS


def test_tool_error_is_returned_to_model_not_raised():
    def broken_search(args, question):
        raise RuntimeError("base indisponible")

    llm = ScriptedLLM([call(requete="fortune"), answer(DONT_KNOW)])
    result = run_agent("Taux ?", adapter=llm, tools=tools(broken_search))

    tool_results = llm.received[1][-1]
    assert isinstance(tool_results, ToolResults)
    assert "erreur" in tool_results.results[0].content
    assert result["trace"][1]["erreur"]
    assert result["reponse"] == DONT_KNOW


def test_identical_call_is_not_executed_twice():
    calls = []

    def counting_search(args, question):
        calls.append(args)
        return fake_search(args, question)

    llm = ScriptedLLM([call(requete="fortune"), call(requete="fortune"), answer(DONT_KNOW)])
    run_agent("Taux ?", adapter=llm, tools=tools(counting_search))

    assert len(calls) == 1
    assert "erreur" in llm.received[2][-1].results[0].content


def test_client_names_never_reach_the_llm_and_are_restored():
    llm = ScriptedLLM([call(ASK_USER_TOOL, questions=["[CLIENT_1] est-elle résidente en Tunisie ?"])])
    result = run_agent("Ma cliente Ben Salah SARL doit-elle payer l'impôt sur la fortune ?", adapter=llm, tools=tools())

    sent = " ".join(m.text for m in llm.received[0] if isinstance(m, UserMessage))
    assert "Ben Salah" not in sent
    assert "[CLIENT_1]" in sent
    assert result["statut"] == "precisions_requises"
    assert result["precisions"] == ["Ben Salah SARL est-elle résidente en Tunisie ?"]


def test_gemini_conversion_pairs_calls_and_results():
    contents = to_gemini_contents([
        UserMessage("Taux ?"),
        AssistantTurn(text="", tool_calls=[ToolCall("rechercher_textes", {"requete": "fortune"}, id="c1")]),
        ToolResults([ToolResult("rechercher_textes", {"passages": []}, call_id="c1")]),
    ])

    assert [c.role for c in contents] == ["user", "model", "user"]
    assert contents[1].parts[0].function_call.id == "c1"
    assert contents[2].parts[0].function_response.id == "c1"


def test_llm_failure_keeps_partial_cost_for_logging():
    class FailingLLM(ScriptedLLM):
        def complete(self, system, messages, tools):
            if self.received:
                raise TimeoutError("Gemini ne répond pas")
            return super().complete(system, messages, tools)

    result = run_agent("Taux ?", adapter=FailingLLM([call(requete="fortune")]), tools=tools())

    assert result["statut"] == "erreur"
    assert result["appels_llm"] == 1
    assert result["tokens_in"] == 100
    assert result["trace"][-1]["type"] == "erreur"


def test_failed_call_can_be_retried_identically():
    attempts = []

    def flaky_search(args, question):
        attempts.append(args)
        if len(attempts) == 1:
            raise TimeoutError("embedding")
        return fake_search(args, question)

    llm = ScriptedLLM([call(requete="fortune"), call(requete="fortune"), answer(DONT_KNOW)])
    run_agent("Taux ?", adapter=llm, tools=tools(flaky_search))

    assert len(attempts) == 2


def test_malformed_clarifications_go_back_to_model():
    llm = ScriptedLLM([
        call(ASK_USER_TOOL, questions="Résidence fiscale ?"),
        call(ASK_USER_TOOL, questions=["Le client est-il résident ?"]),
    ])
    result = run_agent("Combien d'impôt sur la fortune ?", adapter=llm, tools=tools())

    assert "erreur" in llm.received[1][-1].results[0].content
    assert result["statut"] == "precisions_requises"
    assert result["precisions"] == ["Le client est-il résident ?"]


def test_clarification_with_invented_number_is_rejected():
    llm = ScriptedLLM([
        call(ASK_USER_TOOL, questions=["Le seuil étant de 2 millions, le dépasse-t-il ?"]),
        call(ASK_USER_TOOL, questions=["Quelle est la valeur du patrimoine ?"]),
    ])
    result = run_agent("Combien d'impôt sur la fortune ?", adapter=llm, tools=tools())

    assert "2" in llm.received[1][-1].results[0].content["erreur"]
    assert result["precisions"] == ["Quelle est la valeur du patrimoine ?"]


def test_tools_of_the_last_allowed_turn_are_not_executed():
    calls = []

    def counting_search(args, question):
        calls.append(args)
        return fake_search(args, question)

    run_agent("Taux ?", adapter=ScriptedLLM([]), tools=tools(counting_search))

    assert len(calls) == MAX_LLM_CALLS - 1


def test_calculator_rejects_amounts_absent_from_question():
    args = {"resident_in_tunisia": True, "assets": [{"value_tnd": 4_000_000, "location": "tunisie", "category": "autre"}]}
    output = compute_wealth_tax(args, "Mon client a une villa locative, combien d'impôt sur la fortune ?")

    assert "4000000" in output.content["erreur"]
    assert output.passages == []


def test_amounts_in_understands_written_multipliers():
    amounts = amounts_in("Immeubles de 6 MTND, terrain de 2,5 millions, dettes 500 000 dinars, 3 mois")

    assert {Decimal(6_000_000), Decimal(2_500_000), Decimal(500_000)} <= amounts
    assert Decimal(3_000_000) not in amounts


def test_search_rejects_non_numeric_count():
    assert "erreur" in search_texts({"requete": "fortune", "nombre": "beaucoup"}, "").content
