"""Resolve the per-character MOD contract: ids, container names, build paths, atlas inputs."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

ROOT = Path(os.environ.get('PBZ_WORKSPACE_ROOT', Path(__file__).resolve().parents[4]))
PIPELINE = ROOT / 'Pipeline' / 'native-zero'
MODS_DIR = PIPELINE / 'mods'
DEFAULT_PROFILE = 'zero'
MOD_ID_PATTERN = re.compile(r'^zzz_Nte_[A-Za-z]+_P$')

# In-package paths and native dependencies shared by every character MOD. These must never be
# renamed: the cooked mesh references them by path and the game resolves them at runtime.
CONTRACT = {
    'skeleton': '/HuaShira/Characters/Hero/Hero_Hun/Hun_Skin_Skeleton',
    'physics_asset': 'PA_Hun',
    'material_instance': '/Game/PBZContent/Characters/Hero/Hun_New_V2b/Material/MI_ZeroHun_Cap_01_b',
    'texture_package': '/Game/PBZContent/Characters/Hero/Hun_New_V2b/Textures',
    'texture_stem': 'T_ZeroHun_Cap_V02',
    'clothing_static_mesh': 'Content/PBZContent/Characters/Hero/Hun_New_V2b/Mesh/SM_ZeroHun_Cloth_V02.uasset',
    'texture_suffixes': ('BC', 'N', 'ARM'),
    'bones': 264,
    'requires_build': 26367565,
    'target': 'hero',
    'author': 'graydovee',
    'repo_title': 'PhantomBladeZero-NTE-Character-Mod',
}


class Profile:
    def __init__(self, data, source):
        self.source = Path(source)
        self.name = str(data['profile'])
        self.mod_id = str(data['mod_id'])
        if not MOD_ID_PATTERN.match(self.mod_id):
            raise SystemExit('invalid mod id %r in %s (expected zzz_Nte_<Character>_P)' % (self.mod_id, self.source))
        self.title = str(data['name'])
        self.description = str(data.get('description', ''))
        self.build = Path(data['build_dir'])
        if not self.build.is_absolute():
            self.build = ROOT / self.build
        self.release = Path(data['release_dir'])
        if not self.release.is_absolute():
            self.release = ROOT / self.release
        if self.release.name != self.mod_id:
            raise SystemExit('release dir %s does not end with mod id %s' % (self.release, self.mod_id))
        self.source_model = ROOT / data['source_model_dir']
        self.source_checkpoint = ROOT / data['source_checkpoint']
        self.mesh_object = str(data.get('mesh_object', 'SK_' + self.mod_id.split('_')[2] + 'Body'))
        self.atlas_grid = int(data.get('atlas_grid', 4))
        self.atlas_size = int(data.get('atlas_size', 4096))
        self.eye_material = str(data.get('eye_material', 'eye'))
        self.alpha_policy = str(data.get('alpha_policy', 'opaque'))
        self.zip_prefix = str(data.get('zip_prefix') or CONTRACT['repo_title'])
        self.extra = data

    # -- container naming -------------------------------------------------------------------
    @property
    def pak(self):
        return self.mod_id + '.pak'

    @property
    def utoc(self):
        return self.mod_id + '.utoc'

    @property
    def ucas(self):
        return self.mod_id + '.ucas'

    @property
    def container_files(self):
        return (self.pak, self.utoc, self.ucas)

    @property
    def build_rel(self):
        try:
            return self.build.relative_to(ROOT).as_posix()
        except ValueError:
            return str(self.build)

    # -- build artefacts --------------------------------------------------------------------
    def blend(self, stage):
        return self.build / ('%s_%s.blend' % (self.name, stage))

    def fbx(self, stage):
        return self.build / ('%s_%s.fbx' % (self.name, stage))

    def report(self, stage, suffix='json'):
        return self.build / ('%s_%s.%s' % (self.name, stage, suffix))

    def build_file(self, name):
        return self.build / name

    @property
    def container_dir(self):
        return self.build / 'container'

    # -- materials --------------------------------------------------------------------------
    @property
    def texture_stem(self):
        return CONTRACT['texture_stem']

    @property
    def texture_assets(self):
        return [self.texture_package + '/' + CONTRACT['texture_stem'] + '_' + s + '.uasset'
                for s in CONTRACT['texture_suffixes']]

    @property
    def texture_package(self):
        return CONTRACT['texture_package']

    # -- distribution -----------------------------------------------------------------------
    def zip_names(self, version):
        return {
            'mod': '%s-v%s.zip' % (self.mod_id, version),
            'bundle': '%s-%s-v%s.zip' % (self.zip_prefix, self.mod_id, version),
            'nexus': '%s-Nexus-%s-v%s.zip' % (self.zip_prefix, self.mod_id, version),
        }


def load(name=None):
    """Load the active character profile (PBZ_MOD, default zero)."""
    chosen = (name or os.environ.get('PBZ_MOD') or DEFAULT_PROFILE).strip().lower()
    path = MODS_DIR / (chosen + '.json')
    if not path.is_file():
        available = sorted(p.stem for p in MODS_DIR.glob('*.json')) if MODS_DIR.is_dir() else []
        raise SystemExit('unknown character profile %r; available: %s' % (chosen, available))
    data = json.loads(path.read_text(encoding='utf-8'))
    data.setdefault('profile', chosen)
    return Profile(data, path)


def build_dir(profile=None):
    """Build directory honouring PBZ_BUILD_DIR for isolated or legacy runs."""
    p = profile or load()
    override = os.environ.get('PBZ_BUILD_DIR')
    return Path(override) if override else p.build


def require_build_dir(profile=None):
    path = build_dir(profile)
    if not path.is_dir():
        raise SystemExit('build directory not found: %s (run the previous pipeline stage first)' % path)
    return path


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write_json(path, payload):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
