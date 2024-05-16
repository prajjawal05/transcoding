import os
import argparse
import asyncio
from orchestration.storage import store as objstore
from orchestration.orchestrator import BaseOrchestrator

auth = ("23bc46b1-71f6-4ed5-8c54-816aa4f8c502",
        "123zO3xZCLrMN6v2BKK1dXYFpXlPkccOFqm12CdAsMgRU4VrNZ9lyGVCGuMDGIwP")
orch = BaseOrchestrator.BaseOrchestrator(auth)

CHUNKS_BUCKET_NAME = 'output-chunks'
TRANSCODED_CHUNKS_NAME = 'transcoded-chunks'
PROCESSED_VIDEO_BUCKET = 'processed-video'
INPUT_VIDEO_BUCKET = 'input-video'


async def main(input_video):
    num_chunks = 1
    transcoding_parallelisation = 2

    # you need to call start function
    orch.start('video-transcoding')

    orch.store.create_bucket(INPUT_VIDEO_BUCKET)
    orch.store.create_bucket(TRANSCODED_CHUNKS_NAME)
    orch.store.create_bucket(PROCESSED_VIDEO_BUCKET)
    orch.store.create_bucket(CHUNKS_BUCKET_NAME)
    
    video_name = os.path.basename(input_video)
    orch.store.put_sync(INPUT_VIDEO_BUCKET, video_name, input_video, mark=False)

    print("** Chunking **")
    split_action = orch.prepare_action('split', dict(num_chunks = num_chunks, input = video_name))
    split_results = (await orch.make_action([split_action], retries=1))[0]
    if not split_results['success']:
        raise Exception('Error splitting in chunks')

    chunks = split_results['result']['splits']

    print(f"** Transcoding in batches of: {transcoding_parallelisation} **")

    transcoding_actions = []
    for i, chunk in enumerate(chunks):
        transcoding_actions.append(
            orch.prepare_action('transcode', dict(input = chunk, resolution = '360p')))

    trans_results = await orch.make_action(transcoding_actions, retries=1)
    for res in trans_results:
        if not res['success']:
            raise Exception('Some transcoding Unsuccessful')

    # shows the retry feature, in case of NoSuchKeyException
    orch.store.remove_object(TRANSCODED_CHUNKS_NAME, chunks[0])

    print("** Combining **")
    combine_action = orch.prepare_action('combine', dict(input = chunks))
    combine_results = (await orch.make_action([combine_action], object_ownership=False, retries=1))[0]
    if not combine_results['success']:
        raise Exception('Error combining transcoded chunks')

    print("** Done **")
    print("Output available at: {}".format(
        combine_results['result']['output_file']))

    # you need to call stop function
    orch.stop()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-video", required=True)
    args = parser.parse_args()
    asyncio.run(main(args.input_video))
