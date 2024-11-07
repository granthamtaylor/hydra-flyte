# Experiment Configuration with Hydra, Dataclasses, and Flyte

Managing complex configurations for machine learning experiments can be quite challenging.
The scope of configurations can be quite diverse: ranging from managing different databases, datasets, model types and their respective hyperparameters and metrics.
Configurations may also be used to define various preprocessing and feature engineering work associated with a model training pipeline as well as potential model deployment strategies.

Machine learning experimentation best practices dictate that one should _never_ hardcode their configurations, but instead define it elsewhere in a human readable file.
`yaml` has become the most intuitive solution for this, and `hydra` has become the de-facto implementation for managing complex, nested `yaml` configuration files.

While `hydra` is extremely powerful, it's assumptions around how one uses configurations are actually misplaced in the context of workflow orchestration. In short, `hydra` will create an `DictConfig` construct of hierarchical configurations from your selected files. This is one, large single object. However, in the context of workflow orchestration, this approach is inelegant and inefficient for a few reasons.


For one, workflow orchestration tools such as Flyte rely upon strict type checking. A `DictConfig` is a `json`-like blob that is not strictly type checked.

Secondly, and quite related to my prior point, a `DictConfig` has no guardrails against invalid values. For instance: I may have a configuration `lr` that defines the learning rate for my model. `hydra` will not know that `lr` needs to be of type `float`, but it also will not check whether `0. < lr < 1.`. In other words, such "bad" configurations will only be realized during _run time_, whereas ideally one should be able to prevent this at _registration time_.

Lastly, and perhaps most importantly, workflow orchestration benefits from minimal task inputs. In other words, any task in an DAG should have the minimal number of inputs in order to ensure optimal cache performance. If one were to naively input the `DictConfig` to every task in the workflow this would result in extremely poor cache performance. Any single change to any configuration item would guarantee a cache miss on subsequent executions.

However, by supporting workflow programmatic execution and first-class `pydantic` dataclasses, Flyte can seamlessly work around these few obstacles to enable arbitrarily complex workflow configuration for local execution, remote execution, and workflow registration while adhering to best practices.

## Basic Dataclass Definitions

Firstly, a model developer may create arbitrary `pydantic` dataclass constructs that define their configurations:

```python

from pydantic.dataclasses import dataclass

@dataclass
class Column:
    name: str
    dtype: str
    description: str

@dataclass
class Schema:
    target: Column
    features: list[Column]
```

## Advanced Pydantic Validation

Because we are using `pydantic` dataclasses, you may also define arbitrary validation logic for each attribute, including support for `Enum` constructs too:

```python

from typing import Annotated
from enum import Enum

from pydantic.dataclasses import dataclass
from pydantic import Field

class Loss(Enum):

    SQUARED_ERROR = 'squared_error'
    ABSOLUTE_ERROR = 'absolute_error'
    HUBER = 'huber'
    QUANTILE = 'quantile'

@dataclass
class Hyperparameters:
    loss: Loss
    learning_rate: Annotated[float, Field(gt=0.0, lt=1.0)]
    n_estimators:  Annotated[int, Field(ge=1)]
    max_depth: Annotated[int, Field(ge=1)]
    min_samples_split: Annotated[int, Field(ge=1)]

    @validator(mode="after")
    def check_complexity(self):
        """Check whether the model is complex enough."""

        # this will fail should the following assert not succeed
        assert (self.max_depth + self.n_estimators) >= 4, "the model is not complex enough"

        return self

```

These constructs may be as complex and rigorously validated as required for your use case.

## Hydra Hierarchical Configurations

These configurations may be arbitrarily nested, as `hydra` recommends, into one single large `Configuration` dataclass that includes every configuration possible.

```python
@dataclass
class Configuration:
    connection: Connection
    schema: Schema
    hyperparameters: Hyperparameters
```

Now that we have a strictly typed and validated representation of all configurations, we may then begin to define multiple variations of the configurations. For example, you may define multiple database connections: `postgres` and `snowflake`, multiple dataset schemas: `cars` and `planes`, and different model hyperparameter permutations: `large`, `medium`, and `small`. All of these different configurations may exist simultaneously in standalone `yaml` files, as recommended by Hydra.

```bash
.
├── config.yaml
├── connection
│   ├── postgres.yaml
│   └── snowflake.yaml
├── hyperparameters
│   ├── large.yaml
│   ├── medium.yaml
│   └── small.yaml
└── schema
    ├── cars.yaml
    └── planes.yaml
```

One may select which variation of each configuration group they require by either setting default values in `config.yaml` or by passing in arguments via the command line.

For example, I may select the `postgres` connection, a `medium` model size, and the `cars` schema to be the default values by creating a `config.yaml` file like so:
```yaml
defaults:
- connection: postgres
- schema: cars
- hyperparameters: medium
```

However, I may then override the default `schema` to use the `planes.yaml` file instead of `cars.yaml` like so:

```bash
python main.py schema=planes
```

This is merely the tip of the iceberg, however. Hydra supports multi-run executions and much more, such that you may orchestrate multiple concurrent workflow executions.

## Recursive, Automatic Dataclass Instantiation

One may trivially parse through the variations of this configuration bundle inside a `hydra` "app":

```python
@hydra.main(version_base="1.3", config_path="config", config_name="config")
def app(config: DictConfig) -> None:
    print(config)
```

This will return a `DictConfig` object of the nested configurations. However, we can utilize Hydra and Pydantic's marvelous support for one another like so:

```python

@dataclass
class Configuration:
    connection: Connection
    schema: Schema
    hyperparameters: Hyperparameters

@hydra.main(version_base="1.3", config_path="config", config_name="config")
def app(config: DictConfig) -> None:

    config: Configuration = hydra.utils.instantiate(config, _convert_="object", _target_=Configuration)
```

In a single like, this `DictConfig` object will be recursively instantiated into a `Configuration` dataclass instance. All validations and type checks will be performed. Should they fail, they will do so loudly. This is completely, 100% automatic. These dataclasses are the preferred means of managing complex objects in Flyte. 

## Programmatic Workflow Execution

Supposing we have some Flyte Workflow named `my_workflow`, we need a way to programmatically execute it with these dataclass configurations:

```python

import flytekit

@flytekit.workflow
def my_workflow(
    connection: Connection,
    schema: Schema,
    hyperparameters: Hyperparameters,
):
    ...

@hydra.main(version_base="1.3", config_path="config", config_name="config")
def app(config: DictConfig) -> None:
    
    # instantiate dataclasses from DictConfig
    config: Configuration = hydra.utils.instantiate(config, _convert_="object", _target_=Configuration)

    # create Union remote connection
    remote = UnionRemote(default_domain="development", default_project="default")
    
    # execute workflow with configurations
    run = remote.execute(remote.fast_register_workflow(my_workflow), inputs=vars(config))
    
    # print execution URL
    print(run.execution_url)

if __name__ == "__main__":
    app()
```

Upon executing this script, with less than 30 LoC, we can:
1. Collect all of the preferred configurations from our `yaml` files.
2. Coerce the configurations to the instances of the typed `dataclass` constructs.
3. Perform arbitrary validation checks, thus minimizing the risk of runtime errors due to unexpected data types.
4. Connect to a Union cluster.
5. Build the necessary Docker images for the remote executions and bundle your local code for this remote runtime.
6. Execute the workflow `my_workflow` remotely.

## Attribute Access in Workflow DSL

The `flytekit` DSL is extremely flexible, and works especially well with `dataclass` instances. A developer may choose to utilize "fine-grained" caching by passing attributes of a `dataclass` instance to a task instead of the entire `dataclass`. Such "fine-grained" caching enables better chances of a "cache hit" to save significant amounts of both money and time.

As such, one may construct a simple workflow that utilizes the attributes of our dataclasses like so:

```python

image = flytekit.ImageSpec(packages=["flytekit==1.14.0b5", "hydra-core", "pydantic"])

@flytekit.task(container_image=image)
def show_lr(lr: float):

    print(lr)


@flytekit.task(container_image=image)
def show_column(column: Column):

    print(column)

@flytekit.workflow
def my_workflow(
    connection: Connection,
    schema: Schema,
    hyperparameters: Hyperparameters,
):
    
    # use only the "learning_rate" attribute of the "hyperparameters" dataclass
    show_lr(hyperparameters.learning_rate)

    # map over the list of "features" in the "schema" dataclass
    fk.map_task(show_column)(schema.features)
```

With this technique, one may easily use Hydra, Pydantic, and Flyte to manage arbitrarily complex data science projects with ease. Everything is strictly type checked, validated, and cache-efficient.

## Remote, Multi-Run Workflow Executions

Now that we have our configurations all set up, we can easily sweep through multiple variations of our hyperparameters with ease.

With a single command, we will submit 12 concurrently running workflow executions to our remote cluster:

```
python main.py --multirun \
    connection=snowflake,postgres \
    schema=cars,planes \
    hyperparameters=large,medium,small
```

Flyte will manage the caching, even for concurrently running executions, such that should some of these independent workflows require, say, reading the same dataset from the same database, it will "block" redundant executions from duplicating the same work, and instead wait until the outputs of such tasks are available in the cluster's cache. This is yet another awesome bit of synergy among Hydra Pydantic, and Flyte.

