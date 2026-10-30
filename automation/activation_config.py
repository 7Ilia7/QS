"""Produce nonsecret receiver config from the reviewed baseline CI manifest, locally."""
import argparse
import json
from pathlib import Path
from release_lib import validate_manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--baseline-manifest', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    config = {'schema': 'qs.receiver-config.v1', 'baseline_label': 'qc-20261030-existing-v1', 'baseline_manifest': validate_manifest(json.loads(args.baseline_manifest.read_text())), 'mono_id': '7f75e5900b24162f35b9be39dbc8b78c61ee3d4200bf1526129247f561a83e98'}
    with args.output.open('x') as stream:
        json.dump(config, stream, indent=2)
        stream.write('\n')
