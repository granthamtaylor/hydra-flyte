import flytekit as fk
import hydra
from omegaconf import DictConfig

from structs import (
    Configuration, 
    Connection,
    Schema,
    Hyperparameters,
    Column,
)


@fk.task
def show(
    connection: Connection,
    schema: Schema,
    hyperparameters: Hyperparameters
):
    print(f"Connection: {connection}")
    print(f"Schema: {schema}")
    print(f"Hyperparameters: {hyperparameters}")

@fk.task
def iterate(column: Column):
    print(column)

@fk.workflow
def my_workflow(config: Configuration):
    
    show(connection=config.connection, schema=config.schema, hyperparameters=config.hyperparameters)
    fk.map_task(iterate)(column=config.schema.features)
    

@hydra.main(version_base=None, config_path="../config", config_name="config")
def app(config: DictConfig) -> None:
    
    inputs = hydra.utils.instantiate(config, _convert_="object")
    
    my_workflow(inputs)

if __name__ == "__main__":
    app()