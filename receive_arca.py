#!/usr/bin/env python
import pika, sys, os, json

def main():
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
    channel = connection.channel()

    channel.queue_declare(queue='response')

    def callback(ch, method, properties, body):
        try:
            response = json.loads(body)
            print(f" [x] Received response: {json.dumps(response, indent=2)}")
        except json.JSONDecodeError:
            print(f" [x] Received non-JSON message: {body}")

    channel.basic_consume(queue='response', on_message_callback=callback, auto_ack=True)

    print(' [*] Waiting for messages. To exit press CTRL+C')
    channel.start_consuming()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('Interrupted')
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
