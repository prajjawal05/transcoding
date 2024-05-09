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

def main(args):
    print(args)
    store = objstore.ObjectStore(args)

    transcoded_chunks = args["input"]

    print('Starting to combine')
    start = datetime.utcnow()
    epoch = get_epoch()
    video_streams = []
    audio_streams = []

    os.makedirs(TRANSCODED_CHUNKS_NAME, exist_ok=True)
    for chunk in transcoded_chunks:
        input_file_name = os.path.join(TRANSCODED_CHUNKS_NAME, chunk)
        store.get_sync(TRANSCODED_CHUNKS_NAME, chunk, input_file_name)
        input_stream = ffmpeg.input(input_file_name)
        video_streams.append(input_stream.video)
        if input_stream.audio is not None:
            audio_streams.append(input_stream.audio)

    audio_streams = []
    # Use a=0 to avoid audio streams
    concatenated_video = ffmpeg.concat(*video_streams, a=0, v=1)

    os.makedirs(PROCESSED_VIDEO_BUCKET, exist_ok=True)
    output_object_name = f"output_{epoch}.mp4"
    output_file = os.path.join(PROCESSED_VIDEO_BUCKET, output_object_name)

    try:
        if audio_streams:
            concatenated_audio = ffmpeg.concat(*audio_streams, v=0, a=1)
            ffmpeg.output(concatenated_video, concatenated_audio, output_file) \
                .run(overwrite_output=True, quiet=True)
        else:
            ffmpeg.output(concatenated_video, output_file) \
                .run(overwrite_output=True, quiet=True)
    except ffmpeg.Error as e:
        print(f'ffmpeg error\nstdout:\n{e.stdout}\nstderr:\n{e.stderr}')

    end = datetime.utcnow()

    store.put_sync(PROCESSED_VIDEO_BUCKET, output_object_name, output_file)
    print('Completed combining in {}'.format(end-start))
    
    return {
        "output_file": output_file
    }

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", required=True)
    args = parser.parse_args()
    main({
        "context": {
            "action_id": "test-action-chunk"
        },
        "num_chunks": '2',
        "input": args.inputs
    })