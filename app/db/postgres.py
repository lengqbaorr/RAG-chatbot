class PostgresDatabase:
    def __init__(self, dsn: str) -> None:
        self.dsn = dsn

    def initialize(self) -> None:
        raise NotImplementedError("PostgreSQL adapter is reserved for a later phase")
