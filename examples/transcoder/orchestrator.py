import asyncio
from orchestration.storage import store as objstore
from orchestration.orchestrator import BaseOrchestrator

auth = ("23bc46b1-71f6-4ed5-8c54-816aa4f8c502",
        "123zO3xZCLrMN6v2BKK1dXYFpXlPkccOFqm12CdAsMgRU4VrNZ9lyGVCGuMDGIwP")
orch = BaseOrchestrator.BaseOrchestrator(auth)
action_name = 'transcoder'

CHUNKS_BUCKET_NAME = 'output-chunks'
TRANSCODED_CHUNKS_NAME = 'transcoded-chunks'
PROCESSED_VIDEO_BUCKET = 'processed-video'
INPUT_VIDEO_BUCKET = 'input-video'

def get_store():
    return objstore.ObjectStore([CHUNKS_BUCKET_NAME, TRANSCODED_CHUNKS_NAME, 
                                PROCESSED_VIDEO_BUCKET, INPUT_VIDEO_BUCKET])

async def main():
    num_chunks = 5
    transcoding_parallelisation = 2
    store = get_store()

    # you need to call start function
    orch.start('video-transcoding')

    print("** Chunking **")
    params = {
        "type": "chunk",
        "num_chunks": num_chunks,
        "input": "facebook.mp4"
    }

    split_action = orch.prepare_action('splitter', params)
    split_results = (await orch.make_action([split_action]))[0]
    if not split_results['success']:
        raise Exception('Error splitting in chunks')

    chunks = split_results['result']['splits']

    print(f"** Transcoding in batches of: {transcoding_parallelisation} **")

    transcoding_actions = []
    for i, chunk in enumerate(chunks):
        params = {
            "type": "transcode",
            "input": chunk,
            "resolution": "360p"
        }
        # if i % 2 == 0:
        #     params["type"] = "transcodes"
        transcoding_actions.append(
            orch.prepare_action(action_name, params))

    trans_results = await orch.make_action(transcoding_actions)
    for res in trans_results:
        if not res['success']:
            raise Exception('Some transcoding Unsuccessful')

    # shows the retry feature, in case of NoSuchKeyException
    #store.remove_object({}, TRANSCODED_CHUNKS_NAME, chunks[0])

    print("** Combining **")
    params = {
        "type": "combine",
        "input": chunks
    }
    combine_action = orch.prepare_action('combiner', params)
    combine_results = (await orch.make_action([combine_action], object_ownership=False))[0]
    if not combine_results['success']:
        raise Exception('Error combining transcoded chunks')

    print("** Done **")
    print("Output available at: {}".format(
        combine_results['result']['output_file']))

    # you need to call stop function
    orch.stop()

if __name__ == "__main__":
    asyncio.run(main())