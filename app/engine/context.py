class EngineContext:
    """
    Contexto compartido entre los componentes del motor.
    """

    def __init__(self, config: dict):
        self.config = config
        self.metadata = {}
        self.operations = []

    def add_operation(self, operation: str) -> None:
        """
        Registra una operación ejecutada por el motor.
        """

        self.operations.append(operation)
