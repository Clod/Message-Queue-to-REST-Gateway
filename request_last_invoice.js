const amqplib = require('amqplib');
const uuid = require('uuid');
const moment = require('moment');

async function requestLastInvoice(cuit, ptoVta, cbteTipo, timeout = 30) {
    let connection = null;
    try {
        // Establish connection with retry
        connection = await amqplib.connect({
            hostname: 'localhost',
            port: 5672,
            username: 'guest',
            password: 'guest',
            heartbeat: 60,
            channelMax: 5,
            connectionTimeout: 10000,
            authMechanism: ['AMQPLAIN', 'PLAIN'],
            vhost: '/'
        });

        const channel = await connection.createChannel();
        // Declare a temporary exclusive queue for responses
        const result = await channel.assertQueue('', { exclusive: true });
        const callbackQueue = result.queue;

        // Generate a unique correlation ID for this request
        const correlationId = uuid.v4();

        // Store the response when it arrives
        let responseReceived = null;

        const onResponse = (msg) => {
            if (msg.properties.correlationId === correlationId) {
                try {
                    responseReceived = JSON.parse(msg.content.toString());
                } catch (e) {
                    responseReceived = { error: "Failed to parse response as JSON", raw: msg.content.toString() };
                }
            }
        };

        // Set up consumer for the response
        await channel.consume(callbackQueue, onResponse, { noAck: true });

        // Prepare the request message
        const message = {
            cuit: cuit,
            pto_vta: ptoVta,
            cbte_tipo: cbteTipo
        };

        // Send the request
        await channel.publish('', 'arca', Buffer.from(JSON.stringify(message)), {
            replyTo: callbackQueue,
            correlationId: correlationId
        });

        console.log(" [x] Sent request for last invoice, waiting for response...");

        // Wait for the response with timeout
        const startTime = moment();
        while (!responseReceived) {
            if (moment().diff(startTime, 'seconds') > timeout) {
                throw new Error(`No response received after ${timeout} seconds`);
            }
            await new Promise(resolve => setTimeout(resolve, 1000)); // Sleep for 1 second between checks
        }

        return responseReceived;
    } catch (e) {
        if (e.code === 'ECONNREFUSED') {
            console.error("Failed to connect to RabbitMQ");
        } else {
            console.error("An error occurred:", e);
        }
        process.exit(1);
    } finally {
        // Ensure connection is closed even if an error occurs
        if (connection && !connection.closed) {
            await connection.close();
        }
    }
}

async function main() {
    // Example values
    const cuit = "23146234399";
    const ptoVta = "0001";
    const cbteTipo = "001";  // 001 for Factura A

    try {
        const response = await requestLastInvoice(cuit, ptoVta, cbteTipo);
        console.log("\nResponse received:");
        console.log(JSON.stringify(response, null, 2));
    } catch (e) {
        if (e.message.includes("No response received")) {
            console.error("\nTimeout error:", e.message);
        } else {
            console.error("\nError:", e.message);
        }
        process.exit(1);
    }
}

main().catch(console.error);