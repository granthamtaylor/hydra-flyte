from pydantic.dataclasses import dataclass

@dataclass
class Connection:
    driver: str
    username: str
    password: str
    host: str
    port: int
    database: str

@dataclass
class Column:
    name: str
    type: str
    description: str

@dataclass
class Schema:
    target: Column
    features: list[Column]

@dataclass
class Hyperparameters:
    loss: str
    learning_rate: float
    n_estimators: int
    max_depth: int
    min_samples_split: int

@dataclass
class Configuration:
    connection: Connection
    schema: Schema
    hyperparameters: Hyperparameters