import requests
import xml.etree.ElementTree as ET

def send_soap_request(token, cuit, pto_vta, cbte_fch, imp_total, cbte_desde, cbte_hasta, sign):
    """Sends a SOAP request to the AFIP WSFEV1 service (FECAESolicitar) using ElementTree.

    Args:
        token (str): Authentication token.
        cuit (str): CUIT (taxpayer ID).
        pto_vta (int):  Point of Sale.
        cbte_fch (str): Invoice date (YYYYMMDD).
        imp_total (float): Total amount.
        cbte_desde (int): Starting invoice number.
        cbte_hasta (int): Ending invoice number (usually same as starting).
        sign (str): Signature.

    Returns:
        dict: A dictionary containing the response status code and the parsed
              XML response (as an ElementTree object) or the error message.  Returns
              None for the ElementTree if there was an error *before* receiving
              a response.
    """

    # --- Construct SOAP message using ElementTree ---
    soap_ns = "{http://schemas.xmlsoap.org/soap/envelope/}"
    ar_ns = "{http://ar.gov.afip.dif.FEV1/}"

    envelope = ET.Element(soap_ns + "Envelope")
    envelope.set("xmlns:soapenv", "http://schemas.xmlsoap.org/soap/envelope/")
    envelope.set("xmlns:ar", "http://ar.gov.afip.dif.FEV1/")

    header = ET.SubElement(envelope, soap_ns + "Header")
    body = ET.SubElement(envelope, soap_ns + "Body")

    fecae_solicitar = ET.SubElement(body, ar_ns + "FECAESolicitar")
    auth = ET.SubElement(fecae_solicitar, ar_ns + "Auth")
    ET.SubElement(auth, ar_ns + "Token").text = token
    ET.SubElement(auth, ar_ns + "Sign").text = sign
    ET.SubElement(auth, ar_ns + "Cuit").text = cuit

    fecae_req = ET.SubElement(fecae_solicitar, ar_ns + "FeCAEReq")
    fecab_req = ET.SubElement(fecae_req, ar_ns + "FeCabReq")
    ET.SubElement(fecab_req, ar_ns + "CantReg").text = "1"
    ET.SubElement(fecab_req, ar_ns + "PtoVta").text = str(pto_vta)
    ET.SubElement(fecab_req, ar_ns + "CbteTipo").text = "1"

    fedet_req = ET.SubElement(fecae_req, ar_ns + "FeDetReq")
    fecaedet_request = ET.SubElement(fedet_req, ar_ns + "FECAEDetRequest")

    ET.SubElement(fecaedet_request, ar_ns + "Concepto").text = "1"
    ET.SubElement(fecaedet_request, ar_ns + "DocTipo").text = "80"
    ET.SubElement(fecaedet_request, ar_ns + "DocNro").text = "30678186445"
    ET.SubElement(fecaedet_request, ar_ns + "CbteDesde").text = str(cbte_desde)
    ET.SubElement(fecaedet_request, ar_ns + "CbteHasta").text = str(cbte_hasta)
    ET.SubElement(fecaedet_request, ar_ns + "CbteFch").text = cbte_fch
    ET.SubElement(fecaedet_request, ar_ns + "ImpTotal").text = f"{imp_total:.2f}"
    ET.SubElement(fecaedet_request, ar_ns + "ImpTotConc").text = "0"
    ET.SubElement(fecaedet_request, ar_ns + "ImpNeto").text = "150"
    ET.SubElement(fecaedet_request, ar_ns + "ImpOpEx").text = "0"
    ET.SubElement(fecaedet_request, ar_ns + "ImpTrib").text = "7.8"
    ET.SubElement(fecaedet_request, ar_ns + "ImpIVA").text = "26.25"
    ET.SubElement(fecaedet_request, ar_ns + "FchServDesde").text = ""
    ET.SubElement(fecaedet_request, ar_ns + "FchServHasta").text = ""
    ET.SubElement(fecaedet_request, ar_ns + "FchVtoPago").text = ""
    ET.SubElement(fecaedet_request, ar_ns + "MonId").text = "PES"
    ET.SubElement(fecaedet_request, ar_ns + "MonCotiz").text = "1"
    ET.SubElement(fecaedet_request, ar_ns + "CondicionIVAReceptorId").text = "1"

    tributos = ET.SubElement(fecaedet_request, ar_ns + "Tributos")
    tributo = ET.SubElement(tributos, ar_ns + "Tributo")
    ET.SubElement(tributo, ar_ns + "Id").text = "99"
    ET.SubElement(tributo, ar_ns + "Desc").text = "Impuesto Municipal Matanza"
    ET.SubElement(tributo, ar_ns + "BaseImp").text = "150"
    ET.SubElement(tributo, ar_ns + "Alic").text = "5.2"
    ET.SubElement(tributo, ar_ns + "Importe").text = "7.8"

    iva = ET.SubElement(fecaedet_request, ar_ns + "Iva")
    alic_iva1 = ET.SubElement(iva, ar_ns + "AlicIva")
    ET.SubElement(alic_iva1, ar_ns + "Id").text = "5"
    ET.SubElement(alic_iva1, ar_ns + "BaseImp").text = "100"
    ET.SubElement(alic_iva1, ar_ns + "Importe").text = "21"
    alic_iva2 = ET.SubElement(iva, ar_ns + "AlicIva")
    ET.SubElement(alic_iva2, ar_ns + "Id").text = "4"
    ET.SubElement(alic_iva2, ar_ns + "BaseImp").text = "50"
    ET.SubElement(alic_iva2, ar_ns + "Importe").text = "5.25"


    soap_message = ET.tostring(envelope, encoding='utf-8', method='xml')

    headers = {
        "Content-Type": "text/xml;charset=UTF-8",
        "SOAPAction": "http://ar.gov.afip.dif.FEV1/FECAESolicitar",
    }
    url = "https://wswhomo.afip.gov.ar/wsfev1/service.asmx"

    try:
        response = requests.post(url, data=soap_message, headers=headers) # No need to encode here
        response.raise_for_status()

        try:
            root = ET.fromstring(response.content)
            return {"status_code": response.status_code, "response_xml": root, "error": None} # Explicitly set error to None
        except ET.ParseError as parse_err:
            return {
                "status_code": response.status_code,
                "response_xml": None,
                "error": f"XML parsing error: {parse_err}",
            }

    except requests.exceptions.RequestException as e:
        return {"status_code": None, "response_xml": None, "error": str(e)}

def traverse_and_print(element, indent=0):
    """Traverses and prints an ElementTree object with indentation."""
    tag = element.tag.split('}')[-1]  # Remove namespace
    text = (element.text or '').strip() # Get text, handle None, and remove extra whitespace

    print('  ' * indent + f"<{tag}> {text}" )
    for child in element:
        traverse_and_print(child, indent + 1)



if __name__ == "__main__":
    # Example Usage (replace with your actual credentials and data)
    test_token = "token"
    test_sign = "sign"
    test_cuit = "23146234399"
    test_pto_vta = 1
    test_cbte_fch = "20250310"
    test_imp_total = 184.05
    test_cbte_desde = 2
    test_cbte_hasta = 2

    result = send_soap_request(
        test_token, test_cuit, test_pto_vta, test_cbte_fch, test_imp_total, test_cbte_desde, test_cbte_hasta,test_sign
    )

    if result["error"]:
        print(f"Error: {result['error']}")
    else:
        print("Response:")
        print(result)
        print(f"Status Code: {result['status_code']}")
        print("Parsed XML Response:")
        if result["response_xml"] is not None:
          traverse_and_print(result["response_xml"])
        else:
            print(result["response_xml"]) #raw response