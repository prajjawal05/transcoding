from transcoder import actions as action

if __name__ == '__main__':
    action.main({
        "type": "chunk",
        "context": {
            "action_id": "65e518adf0fbb0970bb93fd0",
            "orch_id": "65e518adf0fbb0970bb93fd1"
        },
        "num_chunks": '2',
        "input": "facebook.mp4"
    })
