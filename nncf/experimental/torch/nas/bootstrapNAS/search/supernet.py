import torch
from nncf.experimental.torch.nas.bootstrapNAS.training.model_creator_helpers import resume_compression_from_state
from nncf.torch.model_creation import create_nncf_network
from nncf.torch.checkpoint_loading import load_state


class SuperNetwork:
    def __init__(self, elastic_ctrl, nncf_network):
        self._m_handler = elastic_ctrl.multi_elasticity_handler
        self._elasticity_ctrl = elastic_ctrl
        self._model = nncf_network

    @classmethod
    def from_checkpoint(cls, model, nncf_config, supernet_path, supernet_weights):
        nncf_network = create_nncf_network(model, nncf_config)
        compression_state = torch.load(supernet_path, map_location=torch.device(nncf_config.device))
        model, elasticity_ctrl = resume_compression_from_state(nncf_network, compression_state)
        model_weights = torch.load(supernet_weights, map_location=torch.device(nncf_config.device))
        load_state(model, model_weights, is_resume=True)
        elasticity_ctrl.multi_elasticity_handler.activate_maximum_subnet()
        elasticity_ctrl.multi_elasticity_handler.count_flops_and_weights_for_active_subnet()[0] / 2e6
        return SuperNetwork(elasticity_ctrl, model)

    def get_search_space(self):
        return self._m_handler.get_search_space()

    def get_design_vars_info(self):
        self._m_handler.get_design_vars_info()

    def eval_subnet_with_design_vars(self, design_config, eval_fn, **kwargs):
        self._m_handler.activate_subnet_for_config(self._m_handler.get_config_from_pymoo(design_config))
        return eval_fn(self._model, **kwargs)

    def eval_active_subnet(self, eval_fn, **kwargs):
        return eval_fn(self._model, **kwargs)

    def eval_subnet(self, config, eval_fn, **kwargs):
        self._m_handler.activate_subnet_for_config(config)
        return self.eval_active_subnet(eval_fn, **kwargs)

    def activate_config(self, config):
        self._m_handler.activate_subnet_for_config(config)

    def activate_maximal_subnet(self):
        self._m_handler.activate_maximum_subnet()

    def activate_minimal_subnet(self):
        self._m_handler.activate_minimum_subnet()

    def get_active_config(self):
        return self._m_handler.get_active_config()

    def get_macs_for_active_config(self):
        return self._m_handler.count_flops_and_weights_for_active_subnet()[0] / 2000000

    def export_active_to_onnx(self, filename='subnet'):
        self._elasticity_ctrl.export_model(f"{filename}.onnx")

    def get_config_from_pymoo(self, pymoo_config):
        return self._m_handler.get_config_from_pymoo(pymoo_config)

    def get_active_subnet(self):
        return self._model

