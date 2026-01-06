from fastapi import FastAPI, WebSocket, WebSocketDisconnect
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

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)


manager = ConnectionManager()

async def send_message_to_kafka(message: str):
    producer.produce(KAFKA_CHAT_TOPIC, message.encode('utf-8'))
    producer.flush()

async def consume_messages(websocket: WebSocket, client_id: int):
    current_loop = asyncio.get_running_loop()

    consumer.subscribe([KAFKA_CHAT_TOPIC])
    try:
        while True:
            message = await current_loop.run_in_executor(None, consumer.poll, 1.0)
            if message is None:
                continue
            if message.error():
                print(f"Kafka Consumer error: {message.error()}")
                continue
            await manager.broadcast(f"Client #{client_id} says: {message.value().decode('utf-8')}")
            # msg = consumer.poll(timeout=1.0)
            # if msg is None:
            #     continue
            # if msg.error():
            #     raise KafkaException(msg.error())
            # else:
            #     await websocket.send_text(msg.value().decode('utf-8'))
    except BaseException as e:
        print(f"Error while consuming messages: {e}")
    finally:
        consumer.close()

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: int):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await send_message_to_kafka(data)
            await manager.send_personal_message(f"You wrote: {data}", websocket)
            asyncio.create_task(consume_messages(websocket, client_id))
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast(f"Client #{client_id} left the chat")

@app.get("/")
def read_root():
    return {"message": "Kafka Chat Application is running!"}


@app.get("/chat")
def read_root():
    return FileResponse("python/app/templates/socket_index.html")

# 앱 종료 시 Kafka Consumer 닫기
@app.on_event('shutdown')
async def app_shutdown():
    consumer.close()
