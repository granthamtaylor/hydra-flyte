import flytekit as fk
import hydra
from omegaconf import DictConfig
from union.remote import UnionRemote

from flyte_hydra.structs import Column, Configuration

image = fk.ImageSpec(packages=["flytekit==1.14.0b5", "hydra-core", "pydantic"])

@fk.task(container_image=image)
def show_lr(lr: float):

    print(lr)


@fk.task(container_image=image)
def show_column(column: Column):

    print(column)

@fk.workflow
def my_workflow(config: Configuration):
    
    # use only the "learning_rate" attribute of the "hyperparameters" dataclass
    show_lr(config.hyperparameters.learning_rate)

    # map over the list of "features" in the "schema" dataclass
    fk.map_task(show_column)(config.schema.features)
    

@hydra.main(version_base="1.3", config_path="config", config_name="config")
def app(config: DictConfig) -> None:
    
    # instantiate dataclasses from DictConfig
    config: Configuration = hydra.utils.instantiate(config, _convert_="object", _target_=Configuration)

    # create Union remote connection
    remote = UnionRemote(default_domain="development", default_project="default")
    
    # execute workflow with configurations
    run = remote.execute(remote.fast_register_workflow(my_workflow), inputs={"config": config})
    
    # print execution URL
    print(run.execution_url)

if __name__ == "__main__":
    app()