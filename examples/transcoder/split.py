import os
from orchestration.storage import store as objstore
import ffmpeg

from enum import Enum
from datetime import datetime

CHUNKS_BUCKET_NAME = 'output-chunks'
TRANSCODED_CHUNKS_NAME = 'transcoded-chunks'
PROCESSED_VIDEO_BUCKET = 'processed-video'
INPUT_VIDEO_BUCKET = 'input-video'

def get_epoch():
    return int(datetime.utcnow().timestamp())

def get_video_duration(filename):
    try:
        probe = ffmpeg.probe(filename, v='error',
                            select_streams='v:0', show_entries='stream=duration')
    except ffmpeg.Error as e:
        print(f'ffmpeg error\nstdout:\n{e.stdout}\nstderr:\n{e.stderr}')
    return float(probe['streams'][0]['duration'])

def main(args):
    store = objstore.ObjectStore(args)

    object_name = args["input"]
    num_chunks = int(args["num_chunks"])

    os.makedirs(INPUT_VIDEO_BUCKET, exist_ok=True)
    input_file = f"{INPUT_VIDEO_BUCKET}/{object_name}"
    store.get_sync(INPUT_VIDEO_BUCKET, object_name, input_file)

    print('Starting to chunk')
    duration = get_video_duration(input_file)
    if num_chunks >= duration:
        num_chunks = duration
    print('Video duration is: {}'.format(duration))

    splits = []
    chunk_size = int(duration / num_chunks)
    epoch = get_epoch()

    start = datetime.utcnow()
    os.makedirs(CHUNKS_BUCKET_NAME, exist_ok=True)
    for i in range(num_chunks):
        output_object_name = f"chunk_{i}_{epoch}.mp4"
        output_file = os.path.join(CHUNKS_BUCKET_NAME, output_object_name)

        print('CHUNKING', input_file, output_file, output_object_name)
        try:
            ffmpeg.input(input_file, ss=i * chunk_size, t=chunk_size) \
                  .output(output_file, codec='copy') \
                  .run(overwrite_output=True, quiet=True)
            splits.append(output_object_name)
            store.put_sync(CHUNKS_BUCKET_NAME, output_object_name, output_file)
        except ffmpeg.Error as e:
            print(f'ffmpeg error\nstdout:\n{e.stdout}\nstderr:\n{e.stderr}')

    print("Splits are: {}".format(splits))

    end = datetime.utcnow()

    print('Completed chunking in {}'.format(end-start))

    return {
        "splits": splits
    }

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-video", required=True)
    args = parser.parse_args()
    main({
        "context": {
            "action_id": "test-action-split"
        },
        "num_chunks": '1',
        "input": args.input_video
    })
