from zeep import Client, Settings
from zeep.transports import Transport
from requests import Session
from requests.auth import HTTPBasicAuth
import xml.etree.ElementTree as ET
import os

def solicitar_ultimo_comprobante(token, sign, cuit, pto_vta, cbte_tipo, wsdl_url="https://wswhomo.afip.gov.ar/wsfev1/service.asmx?WSDL"):
    """
    Sends a SOAP message to the AFIP web service to get the last authorized invoice number.

    Args:
        token (str): The token for authentication.
        sign (str): The signature for authentication.
        cuit (str): The CUIT number.
        pto_vta (int): The point of sale.
        cbte_tipo (int): The invoice type.
        wsdl_url (str): The URL of the WSDL file.

    Returns:
        str: The SOAP response.
    """
    session = Session()
    session.auth = HTTPBasicAuth('user', 'pass')
    transport = Transport(session=session)
    settings = Settings(strict=False, xml_huge_tree=True)
    client = Client(wsdl_url, settings=settings, transport=transport)

    envelope = ET.Element("{http://schemas.xmlsoap.org/soap/envelope/}Envelope")
    envelope.set("xmlns:soapenv", "http://schemas.xmlsoap.org/soap/envelope/")
    envelope.set("xmlns:ar", "http://ar.gov.afip.dif.FEV1/")

    header = ET.SubElement(envelope, "{http://schemas.xmlsoap.org/soap/envelope/}Header")
    body = ET.SubElement(envelope, "{http://schemas.xmlsoap.org/soap/envelope/}Body")
    fe_comp_ultimo_autorizado = ET.SubElement(body, "ar:FECompUltimoAutorizado")
    auth = ET.SubElement(fe_comp_ultimo_autorizado, "ar:Auth")
    token_element = ET.SubElement(auth, "ar:Token")
    token_element.text = token
    sign_element = ET.SubElement(auth, "ar:Sign")
    
    sign_element.text = sign
    cuit_element = ET.SubElement(auth, "ar:Cuit")
    cuit_element.text = cuit
    pto_vta_element = ET.SubElement(fe_comp_ultimo_autorizado, "ar:PtoVta")
    pto_vta_element.text = str(pto_vta)
    cbte_tipo_element = ET.SubElement(fe_comp_ultimo_autorizado, "ar:CbteTipo")
    cbte_tipo_element.text = str(cbte_tipo)

    xml_string = ET.tostring(envelope, encoding="unicode")
    response = client.service.FECompUltimoAutorizado(Auth={"Token": token, "Sign": sign, "Cuit": cuit}, PtoVta=pto_vta, CbteTipo=cbte_tipo)
    return response

def main():
    
    cuit = "23146234399"  # Replace with test CUIT
    pto_vta = 1  # Example point of sale
    cbte_tipo = 1  # Example invoice type
    
     # Get the sign from ssl_files/sign.txt
    with open("ssl/ssl_files/token.txt", 'r') as f:
        token = f.read()

    if token is None:
        raise ValueError("ARCA_TOKEN environment variable not set!")

    print(f"Using token: {token[:25]}...")  
    
    # Get the sign from ssl_files/sign.txt
    with open("ssl/ssl_files/sign.txt", 'r') as f:
        sign = f.read()

    if sign is None:
        raise ValueError("ARCA_SIGN environment variable not set!")

    print(f"Using token: {sign[:25]}...")  

    try:
        response = solicitar_ultimo_comprobante(token, sign, cuit, pto_vta, cbte_tipo)
        print("Response:")
        print(response)
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
