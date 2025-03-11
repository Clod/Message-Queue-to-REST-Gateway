from cryptography import x509
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.x509 import load_pem_x509_certificate
from cryptography.hazmat.primitives.serialization import Encoding
from cryptography.hazmat.primitives.serialization import pkcs7
from datetime import datetime, timedelta
from zeep import Client
import base64
import os

'''
This is just a preliminary version. The key is to manage the TA lifecycle correctly:

Request TA: Obtain a TA from WSAA.

Store TA: Persistently store the TA and its expirationTime. This is critical. "Persistently" means it survives restarts of your application or n8n workflow. Options include:

Database: The most robust option (PostgreSQL, MySQL, etc.).

File: Simpler, but less reliable (ensure proper file locking).

n8n Global Variables (with caution): n8n has global variables, but these are not persistent across workflow executions unless you specifically save them to a file or database within the workflow.

Redis or Memcached: If performance is crucial.

Check Expiration: Before making any request to an AFIP business web service (WSN):

Check if you have a stored TA.

If you have a TA, compare the current time with the expirationTime.

If the TA is still valid (current time < expirationTime), use the stored TA.

If the TA is expired or missing, then request a new TA from WSAA.

Reuse TA: Use the valid TA for all subsequent requests to the same WSN until it expires.

Handle Errors Gracefully: Even with careful management, errors can occur (network issues, WSAA downtime). 
Implement retry logic, but avoid immediately requesting a new TA on every error. This could trigger the rate 
limit. Instead, retry with the existing TA a few times, then, after a suitable delay, attempt to get a new TA.
'''

def create_login_ticket_request(service_id):    
    """
    Creates an XML login ticket request for the AFIP WSAA service.

    Args:
        service_id (str): The ID of the service to request access to (e.g., "wsfe").

    Returns:
        bytes: The XML content of the login ticket request.
    """

    # Create XML using standard library
    from xml.etree.ElementTree import Element, SubElement, tostring
    
    root = Element('loginTicketRequest')
    header = SubElement(root, 'header')
    
    now = datetime.now()
    
    unique_id = SubElement(header, 'uniqueId')
    unique_id.text = now.strftime('%y%m%d%H%M')
    
    gen_time = SubElement(header, 'generationTime')
    gen_time.text = (now - timedelta(minutes=10)).strftime('%Y-%m-%dT%H:%M:%S')
    
    exp_time = SubElement(header, 'expirationTime')
    exp_time.text = (now + timedelta(minutes=10)).strftime('%Y-%m-%dT%H:%M:%S')
    
    service = SubElement(root, 'service')
    service.text = service_id
    
    return tostring(root)

def sign_cms(certificate_path, private_key_path, data):
    """
    Signs data using a CMS/PKCS#7 signature.

    Args:
        certificate_path (str): Path to the certificate file.
        private_key_path (str): Path to the private key file.
        data (bytes): The data to be signed.

    Returns:
        bytes: The CMS/PKCS#7 signature.
    """

    # Load certificate
    with open(certificate_path, 'rb') as cert_file:
        cert_data = cert_file.read()
        certificate = load_pem_x509_certificate(cert_data)
    
    # Load private key
    with open(private_key_path, 'rb') as key_file:
        private_key = serialization.load_pem_private_key(
            key_file.read(),
            password=None
        )
    
    # Create CMS/PKCS#7 signature
    options = [pkcs7.PKCS7Options.Binary]
    cms = pkcs7.PKCS7SignatureBuilder().set_data(
        data
    ).add_signer(
        certificate,
        private_key,
        hashes.SHA256()
    ).sign(
        serialization.Encoding.DER,
        options
    )
    
    return cms

def login_ARCA(certificate="certificado_generado.pem", 
         private_key="MiClavePrivadaTest.key",
         service_id="wsfe", # OJO que hay que autorizarlo para este DN (Distinguished Name) en ARCA
         wsaa_wsdl="https://wsaahomo.afip.gov.ar/ws/services/LoginCms?WSDL"):
    
    """
    Main function to request a login ticket from AFIP WSAA.

    Args:
        certificate (str): Path to the certificate file.
        private_key (str): Path to the private key file.
        service_id (str): The ID of the service to request access to.
        wsaa_wsdl (str): The URL of the WSAA WSDL file.
    """
    # Get the directory of the current script
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Construct absolute paths
    certificate_path = os.path.join(script_dir, 'ssl_files', certificate)
    private_key_path = os.path.join(script_dir, 'ssl_files', private_key)

    print(f"Certificate path: {certificate_path}")
    print(f"Private key path: {private_key_path}")

    try:
        # Generate sequence number
        seq_nr = datetime.now().strftime('%Y%m%d%H%S')
        
        # Generate login ticket request
        xml_content = create_login_ticket_request(service_id)
        
        # Sign the content
        cms_signature = sign_cms(certificate_path, private_key_path, xml_content)
        
        # Encode in base64
        cms_base64 = base64.b64encode(cms_signature).decode('utf-8')
        
        # Call WSAA web service
        client = Client(wsaa_wsdl)
        response = client.service.loginCms(cms_base64)
        
        print("Response content:")
        print(response)
        
        # Parse response and save token and sign in a file for debugging purposes
        from xml.etree import ElementTree
        root = ElementTree.fromstring(response)
        credentials = root.find('credentials')
        token = credentials.find('token').text
        sign = credentials.find('sign').text
        
        token_file_path = os.path.join(script_dir, 'ssl_files', 'token.txt')
        sign_file_path = os.path.join(script_dir, 'ssl_files', 'sign.txt')
        
        with open(token_file_path, 'w') as f:
            f.write(token)
            
        with open(sign_file_path, 'w') as f:
            f.write(sign)
               
        print(f"Token saved to ssl_files/token.txt")
        print(f"Sign saved to ssl_files/sign.txt")
        
        return token, sign

    except Exception as e:
        error_msg = str(e)
        print(f"Error: {error_msg}")
        
        # If we get the "already valid TA" error, read and return existing token and sign
        if error_msg == "El CEE ya posee un TA valido para el acceso al WSN solicitado":
            token_file_path = os.path.join(script_dir, 'ssl_files', 'token.txt')
            sign_file_path = os.path.join(script_dir, 'ssl_files', 'sign.txt')
            
            try:
                with open(token_file_path, 'r') as f:
                    token = f.read().strip()
                with open(sign_file_path, 'r') as f:
                    sign = f.read().strip()
                print("Using existing valid token and sign")
                return token, sign
            except Exception as read_error:
                print(f"Error reading existing token/sign: {read_error}")
                raise e
        else:
            # For other errors, write to error log and raise
            loginTicketResponse_ERROR = os.path.join(script_dir, "responses", f"{seq_nr}-loginTicketResponse-ERROR.xml")
            with open(loginTicketResponse_ERROR, 'w') as f:
                f.write(error_msg)
            raise e

if __name__ == "__main__":
    login_ARCA()
