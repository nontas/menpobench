from menpobench import predefined_dir
from menpobench.dataset import retrieve_datasets
from menpobench.errormetric import retrieve_error_metrics
from menpobench.exception import SchemaError
from menpobench.method import (retrieve_trainable_method,
                               retrieve_untrainable_method)
from menpobench.schema import schema_error_report, schema_is_valid
from menpobench.utils import load_yaml, load_schema, memoize


def predefined_experiment_dir():
    return predefined_dir() / 'experiment'


def predefined_experiment_path(name):
    return predefined_experiment_dir() / '{}.yaml'.format(name)


def list_predefined_experiments():
    return sorted([p.stem for p in predefined_experiment_dir().glob('*.yaml')])


@memoize
def experiment_schema():
    return load_schema(predefined_dir() / 'experiment_schema.yaml')


def validate_experiment_def(config):
    s = experiment_schema()
    if not schema_is_valid(s, config):
        report = schema_error_report(s, config)
        raise SchemaError(config, "experiment", report)


def validate_predefined_experiment(name):
    config = load_yaml(predefined_experiment_path(name))
    validate_experiment_def(config)


class Experiment(object):

    def __init__(self, c):
        # Load the experiment and check it's schematically valid
        validate_experiment_def(c)

        self.config = c

        # prepare the error metrics
        self.error_metrics = retrieve_error_metrics(c['error_metric'])

        if 'training_data' in c:
            self.training = retrieve_datasets(c['training_data'])
        self.testing = retrieve_datasets(c['testing_data'], test=True)

        if 'trainable_methods' in c:
            if 'training_data' not in c:
                raise ValueError('Trying to test trainable methods but no '
                                 'training_data was provided')
            self.trainable_methods = [retrieve_trainable_method(m)
                                      for m in c['trainable_methods']]
        else:
            self.trainable_methods = []

        if 'untrainable_methods' in c:
            self.untrainable_methods = [retrieve_untrainable_method(m)
                                        for m in c['untrainable_methods']]
        else:
            self.untrainable_methods = []

    @property
    def training_id(self):
        return self.training.id if self.training is not None else None

    @property
    def testing_id(self):
        return self.testing.id

    def trainable_id(self, trainable_method):
        return {
            'training': self.training_id,
            'trainable_method': trainable_method.id,
            'testing': self.testing.id
        }

    def untrainable_id(self, untrainable_method):
        return {
            'untrainable_method': untrainable_method.id,
            'testing': self.testing.id
        }

    @property
    def all_methods(self):
        return self.trainable_methods + self.untrainable_methods

    @property
    def n_trainable_methods(self):
        return len(self.trainable_methods)

    @property
    def n_untrainable_methods(self):
        return len(self.untrainable_methods)

    @property
    def depends_on_matlab(self):
        for m in self.all_methods:
            if m.depends_on_matlab:
                return True
        return False


def retrieve_experiment(experiment_name):
    if experiment_name.endswith('.yml') or experiment_name.endswith('.yaml'):
        # user is giving a path to an experiment file
        try:
            config = load_yaml(experiment_name)
        except IOError:
            raise ValueError("Requested experiment configuration at path '{}' "
                             "does not exist".format(experiment_name))
    else:
        # predefined experiment
        try:
            config = load_yaml(predefined_experiment_path(experiment_name))
        except IOError:
            raise ValueError("Requested predefined experiment configuration "
                             "'{}' does not exist".format(experiment_name))
    return Experiment(config)
