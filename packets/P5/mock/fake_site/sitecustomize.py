"""Mock only: pretend CUDA exists, and give the frozen load path a synthetic morphology whose descriptor sha256 is
the P4 one (the real path needs the upstream MuJoCo model, which the box does not have)."""
import importlib.abc, importlib.util, sys
import torch
torch.cuda.is_available = lambda: True
P4_DESC = "3c854f91eb3739e4077dfec354d27a33f7c00cf019eec993a8fb43b66b1e5fe3"


class _Hook(importlib.abc.MetaPathFinder):
    def find_spec(self, name, path, target=None):
        if name != "train_entry":
            return None
        sys.meta_path.remove(self)
        spec = importlib.util.find_spec(name)
        orig_exec = spec.loader.exec_module

        def exec_module(mod):
            orig_exec(mod)
            orig = mod.load_morphology

            def load_morphology(cfg, n, info=None):
                cfg = {**cfg, "attention": {**cfg.get("attention", {}), "morphology": "synthetic"}}
                m = orig(cfg, n, info)
                if info is not None and info.get("descriptor_meta"):
                    info["descriptor_meta"] = {**info["descriptor_meta"], "sha256": P4_DESC}
                return m
            mod.load_morphology = load_morphology
        spec.loader.exec_module = exec_module
        return spec


sys.meta_path.insert(0, _Hook())
