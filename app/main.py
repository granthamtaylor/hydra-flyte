import union
import hydra

from structs import Column, Configuration

image = union.ImageSpec(builder="union", packages=["union", "hydra-core", "pydantic"])



@union.task(container_image=image)
def show_config(config: Configuration):

    print(config)


@union.task(container_image=image)
def show_lr(lr: float):

    print(lr)


@union.task(container_image=image)
def show_column(column: Column):

    print(column)

@union.workflow
def my_workflow(config: Configuration):
    
    # show the entire configuration dataclass
    show_config(config)
    
    # use only the "learning_rate" attribute of the "hyperparameters" dataclass
    show_lr(config.hyperparameters.learning_rate)

    # map over the list of "features" in the "structure" dataclass
    union.map_task(show_column)(config.structure.features)
    

@hydra.main(version_base="1.3", config_path="config", config_name="config")
def app(config) -> None:

    # create Union remote connection
    remote = union.UnionRemote(
        default_domain="development",
        default_project="default",
    )
    
    # execute workflow with configurations
    run = remote.execute(
        remote.fast_register_workflow(my_workflow),
        inputs={"config": Configuration(**config)}
    )
    
    # print execution URL
    print(run.execution_url)

if __name__ == "__main__":
    app()