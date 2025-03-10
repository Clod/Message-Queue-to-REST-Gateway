from zeep import Client, Settings
from zeep.transports import Transport
from requests import Session
from requests.auth import HTTPBasicAuth
import os

def send_soap_request(token, sign, cuit, pto_vta, cbte_fch, imp_total, cbte_desde, cbte_hasta, wsdl_url="https://wswhomo.afip.gov.ar/wsfev1/service.asmx?WSDL"):
    """Sends a SOAP request to the AFIP WSFEV1 service (FECAESolicitar) using zeep.

    Args:
        token (str): Authentication token.
        sign (str): Signature.
        cuit (str): CUIT (taxpayer ID).
        pto_vta (int): Point of Sale.
        cbte_fch (str): Invoice date (YYYYMMDD).
        imp_total (float): Total amount.
        cbte_desde (int): Starting invoice number.
        cbte_hasta (int): Ending invoice number (usually same as starting).
        wsdl_url (str): WSDL URL

    Returns:
        dict: A dictionary containing the parsed SOAP response or None if there was an error.
    """
    session = Session()
    session.auth = HTTPBasicAuth('user', 'pass') #Replace with your credentials if needed.  May not be necessary.
    transport = Transport(session=session)
    settings = Settings(strict=False, xml_huge_tree=True)
    client = Client(wsdl_url, settings=settings, transport=transport)

    try:
        response = client.service.FECAESolicitar(
            Auth={
                "Token": token,
                "Sign": sign,
                "Cuit": cuit,
            },
            FeCAEReq={
                "FeCabReq": {
                    "CantReg": 1,
                    "PtoVta": pto_vta,
                    "CbteTipo": 1,
                },
                "FeDetReq": {
                    "FECAEDetRequest": {
                        "Concepto": 1,
                        "DocTipo": 80,
                        "DocNro": "30678186445",  # Replace with actual document number
                        "CbteDesde": cbte_desde,
                        "CbteHasta": cbte_hasta,
                        "CbteFch": cbte_fch,
                        "ImpTotal": imp_total,
                        "ImpTotConc": 0,
                        "ImpNeto": 150,
                        "ImpOpEx": 0,
                        "ImpTrib": 7.8,
                        "ImpIVA": 26.25,
                        "FchServDesde": "",
                        "FchServHasta": "",
                        "FchVtoPago": "",
                        "MonId": "PES",
                        "MonCotiz": 1,
                        "CondicionIVAReceptorId": 1,
                        "Tributos": {
                            "Tributo": {
                                "Id": "99",
                                "Desc": "Impuesto Municipal Matanza",
                                "BaseImp": 150,
                                "Alic": 5.2,
                                "Importe": 7.8,
                            }
                        },
                        "Iva": {
                            "AlicIva": [
                                {"Id": 5, "BaseImp": 100, "Importe": 21},
                                {"Id": 4, "BaseImp": 50, "Importe": 5.25},
                            ]
                        },
                    }
                },
            },
        )
        return response
    except Exception as e:
        print(f"An error occurred: {e}")
        return None


if __name__ == "__main__":

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
    
    cuit = "23146234399"  # Replace with your actual CUIT
    test_pto_vta = 1
    test_cbte_fch = "20250310"
    test_imp_total = 184.05
    test_cbte_desde = 11
    test_cbte_hasta = 11

    result = send_soap_request(
        token, sign, cuit, test_pto_vta, test_cbte_fch, test_imp_total, test_cbte_desde, test_cbte_hasta
    )

    print("Response:")
    print(result)

