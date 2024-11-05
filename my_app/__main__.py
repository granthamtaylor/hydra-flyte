import flytekit as fk
import hydra
from omegaconf import DictConfig
from pydantic.dataclasses import dataclass

from union.remote import UnionRemote


image = fk.ImageSpec(packages=[
    "flytekit==1.14.0b5",
    "hydra-core",
    "pydantic"
])


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

@fk.task(container_image=image)
def show(
    connection: Connection,
    schema: Schema,
    hyperparameters: Hyperparameters
):
    print(f"Connection: {connection}")
    print(f"Schema: {schema}")
    print(f"Hyperparameters: {hyperparameters}")


@fk.task(container_image=image)
def iterate(column: Column):
    print(column)

@fk.workflow
def my_workflow(config: Configuration):
    
    show(connection=config.connection, schema=config.schema, hyperparameters=config.hyperparameters)
    fk.map_task(iterate)(column=config.schema.features)
    

@hydra.main(version_base=None, config_path="../config", config_name="config")
def app(config: DictConfig) -> None:

    remote = UnionRemote(
        default_domain="development",
        default_project="default",
        interactive_mode_enabled=True,
    )
    
    run = remote.execute(my_workflow, inputs={
        "config": hydra.utils.instantiate(config, _convert_="object")
    })
    
    print(run.execution_url)

if __name__ == "__main__":
    app()