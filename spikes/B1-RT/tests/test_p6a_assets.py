"""P6a (B1-P0) CPU tests: asset contract, load-time overlay, AS-1..AS-3 constants, mjlab entity build.

Run from the program root with the P6 CPU env (mujoco 3.16 + mjlab pin)::

    WARP_CACHE_PATH=packets/P6/cpuenv/warp-cache packets/P6/cpuenv/.venv/bin/python -m pytest -q spikes/B1-RT/tests
"""

from __future__ import annotations

import sys
from pathlib import Path

import mujoco
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import home_humanoid as H  # noqa: E402


@pytest.fixture(scope="module")
def hashes_before():
    return H.asset_hashes()


@pytest.fixture(scope="module")
def model():
    return H.load_overlaid_model()


def test_asset_contract(hashes_before):
    assert hashes_before["ok"], hashes_before
    assert hashes_before["xml_sha256"] == H.OWNER_XML_SHA256
    assert hashes_before["n_manifest"] == 27 and not hashes_before["mesh_mismatch"]


def test_owner_model_unmodified_baseline():
    m = mujoco.MjModel.from_xml_path(str(H.asset_xml()))
    assert m.nu == 0  # BLK-1 is a property of the owner file; the overlay clears it at load time
    assert sum(m.geom_type[g] == mujoco.mjtGeom.mjGEOM_PLANE for g in range(m.ngeom)) == 2


def test_structure(model):
    m = model
    assert m.nbody == H.N_BODIES
    assert m.jnt_type[0] == mujoco.mjtJoint.mjJNT_FREE
    assert all(m.jnt_type[j] == mujoco.mjtJoint.mjJNT_HINGE for j in range(1, m.njnt))
    assert m.njnt - 1 == H.NUM_JOINTS == 22


def test_actuators_bLK1(model):
    m = model
    assert m.nu == 22
    targets = tuple(mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_JOINT, m.actuator_trnid[i, 0]) for i in range(m.nu))
    assert targets == H.JOINT_NAMES
    owner = mujoco.MjModel.from_xml_path(str(H.asset_xml()))
    for i, n in enumerate(H.JOINT_NAMES):
        j = owner.joint(n).id
        assert np.allclose(m.actuator_forcerange[i], owner.jnt_actfrcrange[j])
        kp, kd = H.gains(H.group_of(n))
        assert m.actuator_gainprm[i, 0] == pytest.approx(kp)
        assert m.actuator_biasprm[i, 2] == pytest.approx(-kd)
        assert m.dof_armature[m.jnt_dofadr[m.joint(n).id]] == pytest.approx(H.GROUPS[H.group_of(n)]["armature"])


def test_floors_removed_blk5(model):
    planes = [mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_GEOM, g) for g in range(model.ngeom)
              if model.geom_type[g] == mujoco.mjtGeom.mjGEOM_PLANE]
    assert planes == ["scene_floor"]


def test_default_pose_no_self_contact_blk4_blk6(model):
    d = mujoco.MjData(model)
    mujoco.mj_resetDataKeyframe(model, d, model.key("home").id)
    mujoco.mj_forward(model, d)
    floor = model.geom("scene_floor").id
    self_contacts = [c for c in d.contact[: d.ncon] if floor not in (c.geom1, c.geom2)]
    assert not self_contacts
    assert d.ncon >= 2  # both soles touch
    assert np.allclose(d.qpos[7:], H.default_joint_pos())


def test_tracked_bodies_and_feet_as3(model):
    names = {mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, i) for i in range(model.nbody)}
    assert set(H.TRACKED_BODIES) <= names and H.ANCHOR_BODY in names and H.ROOT_BODY in names
    feet = [mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_GEOM, g) for g in range(model.ngeom)]
    import re
    assert sum(bool(re.fullmatch(H.FOOT_GEOM_REGEX, f or "")) for f in feet) == 8
    for s in H.FOOT_SITES:
        model.site(s)


def test_mjlab_entity_cfg():
    from mjlab.entity import Entity

    e = Entity(H.get_home_humanoid_robot_cfg())
    m = e.spec.compile()
    assert m.nu == 22
    targets = tuple(mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_JOINT, m.actuator_trnid[i, 0]) for i in range(m.nu))
    assert targets == H.JOINT_NAMES == tuple(e.joint_names)
    assert not any(m.geom_type[g] == mujoco.mjtGeom.mjGEOM_PLANE for g in range(m.ngeom))
    kp = np.array([H.gains(H.group_of(n))[0] for n in H.JOINT_NAMES])
    assert np.allclose(m.actuator_gainprm[:, 0], kp)


def test_action_scale_matches_d003_rule():
    sc = H.action_scale()
    for g, v in H.GROUPS.items():
        kp, _ = H.gains(g)
        for x in v["expr"]:
            assert sc[x] == pytest.approx(0.25 * v["effort"] / kp)


def test_owner_files_unchanged_after(hashes_before, model):
    after = H.asset_hashes()
    assert after == hashes_before
