from guardrails import Guard, ValidationOutcome, OnFailAction
from guardrails_grhub_exclude_sql_predicates import ExcludeSqlPredicates
from guardrails.hub import ToxicLanguage


class PromptGuards:
    """
    Manages multiple prompt guards for validation.
    """

    def __init__(self):
        """
        Initializes the PromptGuards with predefined guards.
        """
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
        """
        Check if a guard with the given name exists.

        Args:
            name (str): The name of the guard to check.
        Returns:
            bool: True if the guard exists, False otherwise.
        """
        return any(guard.name == name for guard in self.guards)

    def validate(self, name: str, prompt: str) -> ValidationOutcome:
        """
        Validate a prompt against a specified guard.

        Args:
            name (str): The name of the guard to use for validation.
            prompt (str): The prompt to validate.
        Returns:
            ValidationOutcome: The result of the validation.
        Raises:
            ValueError: If the specified guard does not exist.
        """
        guard = self._get_guard(name)
        return guard.validate(prompt)

    def _get_guard(self, name: str) -> Guard:
        for guard in self.guards:
            if guard.name == name:
                return guard
        raise ValueError(f"Guard '{name}' not found")
