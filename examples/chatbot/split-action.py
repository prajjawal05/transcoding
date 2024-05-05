import json
import numpy as np
import time
from object_store import store
from constants import MONGO_HOST, MONGO_PORT, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, MINIO_ENDPOINT

config = dict(STORAGE_ENDPOINT=MINIO_ENDPOINT,
              AWS_ACCESS_KEY_ID=AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY=AWS_SECRET_ACCESS_KEY)


bucket_name = "chatbdat"
store = store.ObjectStore(config, [bucket_name],
                          db_config={'MONGO_HOST': MONGO_HOST,
                                     'MONGO_PORT': MONGO_PORT}
                          )


def upload_matrix(context, A, filename):
    np.savetxt("chatbdat/" + filename, A)
    store.put_sync(context, bucket_name, filename)


def upload_BOW(context, BOW):
    with open('chatbdat/bos.txt', 'w') as f:
        for word in BOW:
            f.write(word + '\n')
    f.close()
    store.put_sync(context, bucket_name, 'bos.txt')


def handler(filename, event):
    context = event['context']
    Network_Bound = event["Network_Bound"]
    start_time = int(round(time.time() * 1000))
    data = []
    with open(filename, 'r') as file:
        data = file.read().replace('\n', '')

    j_data = json.loads(data)
    all_unique_words = []

    all_intents = []
    for v in range(len(j_data["intents"])):
        newIntent = {}
        newIntent["name"] = j_data["intents"][v]["intent"]
        newIntent["data"] = j_data["intents"][v]["text"]
        newIntent["data"].extend(j_data["intents"][v]["responses"])
        for utterance in newIntent["data"]:
            words_list = utterance.split(" ")
            all_unique_words.extend(words_list)
        all_intents.append(newIntent)
        # print(newIntent)
        # print("*************")
        # print("*************")
    BOW = set(all_unique_words)
    All_matrices = []
    for newIntent in all_intents:
        print(newIntent["name"])
        list_vectors = []
        for utterance in newIntent["data"]:
            words_list = utterance.split(" ")
            vector = [int(w in words_list) for w in BOW]
            # print(vector)
            list_vectors.append(vector)
        A = np.array(list_vectors)
        All_matrices.append(A)

    end_time = int(round(time.time() * 1000))
    print("duration before upload:" + str(end_time-start_time))

    returnedDic = {}
    returnedDic["detail"] = {}
    returnedDic["detail"]["indeces"] = []
    bundle_size = event["bundle_size"]
    list_of_inputs_to_bundle = []

    for mat_index in range(len(All_matrices)):
        positive_A = All_matrices[mat_index]
        negative_A = []
        if (mat_index > len(All_matrices) - 4):

            negative_A = All_matrices[0]
            negative_A = np.concatenate((negative_A, All_matrices[1]), axis=0)
            negative_A = np.concatenate((negative_A, All_matrices[2]), axis=0)

        else:
            negative_A = All_matrices[mat_index+1]
            negative_A = np.concatenate(
                (negative_A, All_matrices[mat_index+2]), axis=0)
            negative_A = np.concatenate(
                (negative_A, All_matrices[mat_index+3]), axis=0)

        if (Network_Bound == 1):
            upload_matrix(context, positive_A,
                          all_intents[mat_index]["name"] + "_pos.txt")
            upload_matrix(context, negative_A,
                          all_intents[mat_index]["name"] + "_neg.txt")

        j = {"intent_name": all_intents[mat_index]["name"],
             "skew": event["skew"], "Network_Bound": event["Network_Bound"]}
        list_of_inputs_to_bundle.append(j)
        if (len(list_of_inputs_to_bundle) >= bundle_size):
            newDict = {}
            newDict["values"] = list_of_inputs_to_bundle
            end_time = int(round(time.time() * 1000))
            newDict["duration"] = end_time - start_time
            returnedDic["detail"]["indeces"].append(newDict)
            list_of_inputs_to_bundle = []

    upload_BOW(context, BOW)
    end_time = int(round(time.time() * 1000))
    if (len(list_of_inputs_to_bundle) > 0):
        newDict = {}
        newDict["values"] = list_of_inputs_to_bundle
        newDict["duration"] = end_time - start_time
        returnedDic["detail"]["indeces"].append(newDict)

    print(returnedDic)

    return {
        "results": returnedDic
    }


def main(args):
    if ('dummy' in args) and (args['dummy'] == 1):
        print("Dummy call, doing nothing")
        return {"Message": "Dummy call to Split Chatbot"}
    try:
        return handler("Intent.json", args)
    except Exception as e:
        return {
            "error": {
                'code': getattr(e, 'code', None),
                "message": str(e),
                'meta': getattr(e, 'meta', None)
            }
        }


if __name__ == '__main__':
    main({
        "skew": 4,
        "bundle_size": 1,
        "Network_Bound": 1,
        "context": {
            "action_id": "65e518adf0fbb0970bb93fd0",
            "orch_id": "65e518adf0fbb0970bb93fd0",
        },
    })
