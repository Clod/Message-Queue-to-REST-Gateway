# RabbitMQ ARCA Integration Service

## Project Overview

This project implements a message queue-based gateway between client applications and ARCA (AFIP's Remote Authentication Service). It uses RabbitMQ as the message broker to handle asynchronous communication between clients and the ARCA SOAP service.

### Architecture

The system consists of several components:

1. **Message Broker**: RabbitMQ server handling message queues
2. **Client Interface**: Python and Node.js scripts for sending requests
3. **Service Worker**: Main service (merry_go_round.py) that processes requests
4. **Authentication Module**: Handles ARCA authentication (login_arca.py)
5. **Response Handlers**: Scripts for receiving and processing responses

```
[Client Applications] 
       ↓ ↑
   [RabbitMQ]
       ↓ ↑
[Service Worker (merry_go_round.py)]
       ↓ ↑
 [ARCA SOAP Service]
```

### Queues
- `arca`: Main queue for incoming requests
- `response`: Queue for responses back to clients

## Dependencies

### Python Dependencies (requirements.txt)
- pika: RabbitMQ client library
- cryptography: For SSL/security operations
- zeep: SOAP client for ARCA web services

### Node.js Dependencies (package.json)
- amqplib: RabbitMQ client library
- moment: Date/time handling
- uuid: Generating unique identifiers

## Detailed Script Explanations

### Basic RabbitMQ Examples

#### send.py
Basic RabbitMQ publisher example that:
- Connects to RabbitMQ on localhost
- Declares a queue named 'hello'
- Publishes a simple message

#### receive.py
Basic RabbitMQ consumer that:
- Connects to RabbitMQ
- Listens on the 'hello' queue
- Prints received messages
- Handles graceful shutdown on CTRL+C

### ARCA Integration Scripts

#### request_last_invoice.js and request_last_invoice.py
Client implementations in both Node.js and Python that:
- Establish RabbitMQ connections with retry logic
- Create temporary exclusive response queues
- Generate unique correlation IDs for request tracking
- Handle timeouts and connection errors
- Process JSON responses
- Provide a clean interface for requesting last invoice information

#### solicitud_ultimo_comprobante.py
SOAP client implementation that:
- Interacts directly with AFIP's web service
- Constructs and sends SOAP messages
- Handles authentication with token and sign
- Makes requests for last authorized invoice numbers
- Processes SOAP responses
- Supports both testing and production WSDL endpoints

#### solicitud_factura_a.py and solicitud_factura_a-bien.py
Two implementations for creating AFIP invoices:
1. solicitud_factura_a.py:
   - Uses zeep library for SOAP client functionality
   - Handles invoice creation with detailed parameters
   - Supports tax and VAT calculations
   - Manages authentication and request formatting

2. solicitud_factura_a-bien.py:
   - Alternative implementation using ElementTree
   - Direct XML construction and manipulation
   - More granular control over SOAP message structure
   - Includes detailed response parsing and error handling
   - Provides XML traversal utilities for debugging

#### merry_go_round.py
Main service worker that:
- Manages RabbitMQ connections and channels
- Processes incoming messages from 'arca' queue
- Handles ARCA authentication through login_arca.py
- Makes requests to ARCA service
- Sends responses back through reply queues
- Implements error handling and message acknowledgment
- Supports environment variable configuration for RabbitMQ connection

#### send_arca.py
ARCA-specific publisher that:
- Sends structured JSON messages for invoice requests
- Includes required fields: cuit, pto_vta, cbte_tipo
- Sets up response routing with correlation IDs

#### receive_arca.py
ARCA response consumer that:
- Listens on the 'response' queue
- Parses JSON responses
- Handles both successful responses and errors
- Provides formatted output of responses

### Authentication Module

#### ssl/login_arca.py
Handles ARCA authentication:
- Creates and signs login ticket requests
- Manages certificate-based authentication
- Implements token caching and expiration handling
- Provides error handling and retry logic
- Supports both production and testing environments

## SSL Configuration

The project requires SSL certificates for ARCA authentication:
- Certificate files should be placed in ssl/ssl_files/
- Supports both testing and production certificates
- Manages token lifecycle and caching

## Usage Examples

1. Start the RabbitMQ server:
```bash
docker run -d -p 5672:5672 --name some-rabbit rabbitmq:3
```

2. Start the service worker:
```bash
python merry_go_round.py
```

3. Send last invoice number request:
```python
# Using send_arca.py
message = {
    "cuit": "23146234399",
    "pto_vta": "0001",
    "cbte_tipo": "001"
}
```

4. Receive responses:
```bash
python receive_arca.py
```

## Environment Variables

The service supports configuration through environment variables:
- RABBITMQ_HOST (default: "localhost")
- RABBITMQ_PORT (default: 5672)
- RABBITMQ_USER (default: "guest")
- RABBITMQ_PASSWORD (default: "guest")

## Error Handling

The system implements comprehensive error handling:
- Invalid message format detection
- Missing parameter validation
- ARCA authentication failures
- Network connectivity issues
- Message publishing errors
