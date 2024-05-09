import os
from orchestration.storage import store as objstore
import ffmpeg

from enum import Enum
from datetime import datetime

CHUNKS_BUCKET_NAME = 'output-chunks'
TRANSCODED_CHUNKS_NAME = 'transcoded-chunks'
PROCESSED_VIDEO_BUCKET = 'processed-video'
INPUT_VIDEO_BUCKET = 'input-video'

class Resolution(Enum):
    _360p = "360p"
    _480p = "480p"
    _720p = "720p"
    _1080p = "1080p"

resolution_scale = {
    Resolution._360p.name: '480:360',
    Resolution._480p.name: '858:480',
    Resolution._720p.name: '1280:720',
    Resolution._1080p.name: '1920:1080'
}

def main(args):
    store = objstore.ObjectStore(args)

    chunk_name = args["input"]
    resolution_format = Resolution(args["resolution"])

    start = datetime.utcnow()

    print(f'Processing chunk - {chunk_name}')

    os.makedirs(CHUNKS_BUCKET_NAME, exist_ok=True)
    input_chunk_file = os.path.join(CHUNKS_BUCKET_NAME, chunk_name)
    store.get_sync(CHUNKS_BUCKET_NAME, chunk_name, input_chunk_file)

    os.makedirs(TRANSCODED_CHUNKS_NAME, exist_ok=True)
    output_file = os.path.join(TRANSCODED_CHUNKS_NAME, chunk_name)
    vf = 'scale={}'.format(resolution_scale[resolution_format.name])
    print('ffmpeg', input_chunk_file, output_file)
    try:
        ffmpeg.input(input_chunk_file) \
              .output(output_file, vcodec='libx264', acodec='aac', vf=vf) \
              .run(overwrite_output=True, quiet=True)
    except ffmpeg.Error as e:
        print(f'ffmpeg error\nstdout:\n{e.stdout}\nstderr:\n{e.stderr}')

    store.put_sync(TRANSCODED_CHUNKS_NAME, chunk_name, output_file)

    end = datetime.utcnow()
    print(f'Transcoded input_file in {end-start}')

    return {
        "output_file": chunk_name
    }

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-video", required=True)
    args = parser.parse_args()
    main({
        "context": {
            "action_id": "test-action-transcode"
        },
        "resolution": '360p',
        "input": args.input_video
    })
