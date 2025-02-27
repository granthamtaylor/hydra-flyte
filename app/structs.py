from typing import Annotated
from enum import StrEnum

from pydantic import BaseModel, Field, model_validator

class Connection(BaseModel):
    driver: str
    username: str
    password: str
    host: str
    port: int
    database: str

class Column(BaseModel):
    name: str
    type: str
    description: str

class Structure(BaseModel):
    target: Column
    features: list[Column]
    
class Loss(StrEnum):

    SQUARED_ERROR = 'squared_error'
    ABSOLUTE_ERROR = 'absolute_error'
    HUBER = 'huber'
    QUANTILE = 'quantile'

class Hyperparameters(BaseModel):
    loss: Loss
    learning_rate: Annotated[float, Field(gt=0.0, lt=1.0)]
    n_estimators: Annotated[int, Field(ge=1)]
    max_depth: Annotated[int, Field(ge=1)]
    min_samples_split: Annotated[int, Field(ge=1)]

    @model_validator(mode="after")
    def check_complexity(self):
        """Check whether the model is complex enough."""
        
        assert (self.max_depth + self.n_estimators) >= 4, "the model is not complex enough"

        return self


class Configuration(BaseModel):
    connection: Connection
    structure: Structure
    hyperparameters: Hyperparameters