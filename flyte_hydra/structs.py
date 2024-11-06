from typing import Annotated
from enum import Enum

from pydantic.dataclasses import dataclass
from pydantic import Field, model_validator as validator

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
    
class Loss(Enum):

    SQUARED_ERROR = 'squared_error'
    ABSOLUTE_ERROR = 'absolute_error'
    HUBER = 'huber'
    QUANTILE = 'quantile'

@dataclass
class Hyperparameters:
    loss: Loss
    learning_rate: Annotated[float, Field(gt=0.0, lt=1.0)]
    n_estimators: Annotated[int, Field(ge=1)]
    max_depth: Annotated[int, Field(ge=1)]
    min_samples_split: Annotated[int, Field(ge=1)]

    @validator(mode="after")
    def check_complexity(self):
        """Check whether the model is complex enough."""
        
        assert (self.max_depth + self.n_estimators) >= 4, "the model is not complex enough"

        return self


@dataclass
class Configuration:
    connection: Connection
    schema: Schema
    hyperparameters: Hyperparameters