import asyncio
from BaseOrchestrator import BaseOrchestrator

auth = ("23bc46b1-71f6-4ed5-8c54-816aa4f8c502",
        "123zO3xZCLrMN6v2BKK1dXYFpXlPkccOFqm12CdAsMgRU4VrNZ9lyGVCGuMDGIwP")
orch = BaseOrchestrator(auth)


async def main():
    print("** Split Action **")
    params = {
        "skew": 4,
        "bundle_size": 1,
        "Network_Bound": 1
    }

    orch.start('chatbot')

    split_action = orch.prepare_action('split-action', params)
    split_results = (await orch.make_action([split_action]))[0]
    if not split_results['success']:
        raise Exception('Error splitting in chunks')

    split_results = (split_results['result']['results']['detail']['indeces'])

    print("** Classifier Action **")

    classifying_actions = []
    for i, chunk in enumerate(split_results):
        params = chunk
        # if i % 2 == 0:
        #     params["type"] = "transcodes"
        classifying_actions.append(
            orch.prepare_action('train-classifier', params))

    results = await orch.make_action(classifying_actions, parallelisation=3)
    for res in results:
        if not res['success']:
            raise Exception('Error in classification')

    print(res)
    print("** Done **")
    # print("Output available at: {}".format(
    #     combine_results['result']['output_file']))

    orch.stop()


if __name__ == "__main__":
    asyncio.run(main())
    # poller(['22b0335cebae4d4fb0335cebaefd4fff'])

# had to remove svd part
