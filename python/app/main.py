from fastapi import FastAPI, WebSocket
from confluent_kafka import Producer, Consumer, KafkaException
import asyncio
from fastapi.middleware.cors import CORSMiddleware

from starlette.responses import FileResponse

app = FastAPI()

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Kafka 설정
KAFKA_BOOTSTRAP_SERVERS = 'localhost:9092'
KAFKA_CHAT_TOPIC = 'chat-topic'

# Kafka 프로듀서 설정
producer_config = {
    'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS
}
producer = Producer(producer_config)

# Kafka 컨슈머 설정
consumer_config = {
    'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS,
    'group.id': 'chat-group',
    'auto.offset.reset': 'earliest'
}
consumer = Consumer(consumer_config)

async def send_message_to_kafka(message: str):
    producer.produce(KAFKA_CHAT_TOPIC, message.encode('utf-8'))
    producer.flush()

async def consume_messages(websocket: WebSocket):
    consumer.subscribe([KAFKA_CHAT_TOPIC])
    try:
        while True:
            msg = consumer.poll(timeout=1.0)
            if msg is None:
                continue
            if msg.error():
                raise KafkaException(msg.error())
            else:
                await websocket.send_text(msg.value().decode('utf-8'))
    except BaseException as e:
        print(f"Error while consuming messages: {e}")
    finally:
        consumer.close()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    await websocket.send_text("Welcome to the chat!")
    try:
        consumer_task = asyncio.create_task(consume_messages(websocket))

        while True:
            data = await websocket.receive_text()
            await send_message_to_kafka(data)

    except Exception as e:
        print(f"WebSocket connection error: {e}")
    finally:
        await websocket.close()
        consumer_task.cancel()

@app.get("/")
def read_root():
    return {"message": "Kafka Chat Application is running!"}


@app.get("/chat")
def read_root():
    return FileResponse("python/app/templates/index.html")
