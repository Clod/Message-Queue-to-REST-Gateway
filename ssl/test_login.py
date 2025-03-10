from cryptography import x509
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.x509 import load_pem_x509_certificate
from cryptography.hazmat.primitives.serialization import Encoding
from cryptography.hazmat.primitives.serialization import pkcs7
from datetime import datetime, timedelta
from zeep import Client
import base64

def create_login_ticket_request(service_id):
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

def main(certificate="ssl_files/certificado_generado.pem", 
         private_key="ssl_files/MiClavePrivadaTest.key",
         service_id="wsfe", # OJO que hay que autorizarlo para este DN (Distinguished Name) en ARCA
         wsaa_wsdl="https://wsaahomo.afip.gov.ar/ws/services/LoginCms?WSDL"):
    
    try:
        # Generate sequence number
        seq_nr = datetime.now().strftime('%Y%m%d%H%S')
        
        # Generate login ticket request
        xml_content = create_login_ticket_request(service_id)
        
        # Save XML for debugging
        xml_filename = f"responses/{seq_nr}-LoginTicketRequest.xml"
        with open(xml_filename, 'wb') as f:
            f.write(xml_content)
        print(f"XML saved to {xml_filename}")
        
        # Sign the content
        cms_signature = sign_cms(certificate, private_key, xml_content)
        
        # Encode in base64
        cms_base64 = base64.b64encode(cms_signature).decode('utf-8')

        # Save CMS signature for debugging
        cms_filename = f"responses/{seq_nr}-cms_signature.txt"
        with open(cms_filename, 'w') as f:
            f.write(cms_base64)
        print(f"CMS signature saved to {cms_filename}")
        
        # Call WSAA web service
        client = Client(wsaa_wsdl)
        response = client.service.loginCms(cms_base64)
        
        # Save and print response
        with open(f"responses/{seq_nr}-loginTicketResponse.xml", 'w') as f:
            f.write(response)
        
        print(f"Response saved to solicitud_desde_mac/{seq_nr}-loginTicketResponse.xml")
        print("Response content:")
        print(response)
        
    except Exception as e:
        error_msg = str(e)
        print(f"Error: {error_msg}")
        with open(f"{seq_nr}-loginTicketResponse-ERROR.xml", 'w') as f:
            f.write(error_msg)

if __name__ == "__main__":
    main()
