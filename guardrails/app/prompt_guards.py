from guardrails import Guard, ValidationOutcome, OnFailAction
from guardrails_grhub_exclude_sql_predicates import ExcludeSqlPredicates
from guardrails.hub import ToxicLanguage


class PromptGuards:

    def __init__(self):
        sql_guard = Guard()
        sql_guard.name = 'sql'
        sql_guard.use(
            ExcludeSqlPredicates,
            predicates=["Drop", "Update", "Delete", "Create", "Alter", "Insert"],
            on_fail=OnFailAction.EXCEPTION)
        toxic_guard = Guard()
        toxic_guard.name = 'toxic'
        toxic_guard.use(ToxicLanguage, threshold=0.5, validation_method="sentence", on_fail=OnFailAction.EXCEPTION)
        self.guards = [sql_guard, toxic_guard]

    def is_guard(self, name: str) -> bool:
        return any(guard.name == name for guard in self.guards)

    def validate(self, name: str, prompt: str) -> ValidationOutcome:
        guard = self._get_guard(name)
        return guard.validate(prompt)

    def _get_guard(self, name: str) -> Guard:
        for guard in self.guards:
            if guard.name == name:
                return guard
        raise ValueError(f"Guard '{name}' not found")
