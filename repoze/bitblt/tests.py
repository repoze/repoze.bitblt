import unittest
import base64

from StringIO import StringIO

class TestProfileMiddleware(unittest.TestCase):
    def _makeOne(self, *arg, **kw):
        from repoze.bitblt.processor import ImageTransformationMiddleware
        return ImageTransformationMiddleware(*arg, **kw)

    def test_scaling(self):
        middleware = self._makeOne(None)
        image = middleware.process(
            StringIO(jpeg_image_data), (32, 32), 'image/jpeg')
        self.assertEqual(image.size, (32, 32))

    def test_call_content_type_not_image(self):
        environ = {}
        body = "<html><body>Hello, world!</body></html>"
        
        def mock_app(environ, start_response):
            start_response('200 OK', [('content-type', 'text/html'),
                                      ('content-length', str(len(body)))])
            return (body,)

        response = []
        def start_response(*args):
            response.extend(args)

        middleware = self._makeOne(mock_app)
        result = middleware(environ, start_response)
        self.assertEqual(result, (body,))
        self.assertEqual(response, [
            '200 OK', [('content-type', 'text/html'), ('content-length', '39')], None])
        
    def test_call_content_type_is_image(self):
        environ = {
            'mimetype': 'image/jpeg',
            'width': '32',
            'height': '32'}

        response = []

        def mock_start_response(status, headers, exc_info=None):
            response.append(status)
            response.extend(headers)
            
        def mock_app(environ, start_response):
            body = jpeg_image_data
            start_response('200 OK', [('content-type', 'image/jpeg'),
                                      ('content-length', str(len(body)))])
            return (body,)

        middleware = self._makeOne(mock_app)
        result = middleware(environ, mock_start_response)
        self.assertEqual(len("".join(result)), 3072)
        self.assertEqual(response, [
            '200 OK', ('content-type', 'image/jpeg'), ('content-length', '3072'), None])
        
jpeg_image_data = base64.decodestring("""\
/9j/4AAQSkZJRgABAQEASABIAAD/4gPwSUNDX1BST0ZJTEUAAQEAAAPgYXBwbAIAAABtbnRyUkdC
IFhZWiAH1gAFABcADwALAAthY3NwQVBQTAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA9tYAAQAA
AADTLWFwcGwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA5y
WFlaAAABLAAAABRnWFlaAAABQAAAABRiWFlaAAABVAAAABR3dHB0AAABaAAAABRjaGFkAAABfAAA
ACxyVFJDAAABqAAAAA5nVFJDAAABuAAAAA5iVFJDAAAByAAAAA52Y2d0AAAB2AAAADBuZGluAAAC
CAAAADhkZXNjAAACQAAAAGhkc2NtAAACqAAAAN5tbW9kAAADiAAAAChjcHJ0AAADsAAAAC1YWVog
AAAAAAAAfmkAAEC2AAABklhZWiAAAAAAAABU7AAApucAABbfWFlaIAAAAAAAACOBAAAYeQAAurZY
WVogAAAAAAAA89gAAQAAAAEWCHNmMzIAAAAAAAELtwAABZb///NXAAAHKQAA/df///u3///9pgAA
A9oAAMD2Y3VydgAAAAAAAAABAc0AAGN1cnYAAAAAAAAAAQHNAABjdXJ2AAAAAAAAAAEBzQAAdmNn
dAAAAAAAAAABAADRdAAAAAAAAQAAAADRdAAAAAAAAQAAAADRdAAAAAAAAQAAbmRpbgAAAAAAAAAw
AACmwAAAVgAAAEoAAACbwAAAJAAAABZAAABQQAAAVEAAAjMzAAIzMwACMzNkZXNjAAAAAAAAAA5W
QTIwMTJ3U0VSSUVTAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAG1sdWMAAAAAAAAADwAAAAxpdElUAAAA
GgAAAMRmckZSAAAAGgAAAMRlc0VTAAAAGgAAAMRmaUZJAAAAGgAAAMRwdFBUAAAAGgAAAMR6aFRX
AAAAGgAAAMRqYUpQAAAAGgAAAMRubE5MAAAAGgAAAMRkZURFAAAAGgAAAMRrb0tSAAAAGgAAAMRl
blVTAAAAGgAAAMRub05PAAAAGgAAAMRzdlNFAAAAGgAAAMRkYURLAAAAGgAAAMR6aENOAAAAGgAA
AMQAVgBBADIAMAAxADIAdwBTAEUAUgBJAEUAUwAAbW1vZAAAAAAAAFpjAABqHAAAAADAORUAAAAA
AAAAAAAAAAAAAAAAAHRleHQAAAAAQ29weXJpZ2h0IEFwcGxlIENvbXB1dGVyLCBJbmMuLCAyMDAz
AAAAAP/bAEMAAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEB
AQEBAQEBAQEBAQEBAQEBAf/bAEMBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEB
AQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAf/AABEIADAAMAMBEQACEQEDEQH/xAAeAAACAAYD
AAAAAAAAAAAAAAAKCwEDBQYHCQACCP/EAC4QAAAGAQMDAwEJAQAAAAAAAAECAwQFBgcIERIJISIA
ChNBFBUjMTIzQlFSYf/EABQBAQAAAAAAAAAAAAAAAAAAAAD/xAAUEQEAAAAAAAAAAAAAAAAAAAAA
/9oADAMBAAIRAxEAPwA/UxylARMIAAAIiI9gAA/MRH6AG/c309BKMYFClEgibc3gJQ5F5fQ+3Yp0
yCPPluBeRSfz9AMZ1VvdB6PunJkmbwHjmky+rzUPT5QYjIdRplziaLjPGsizAAkqzdMsuq3dl18i
xKiqachTarTbEnAyScjA3ObqVhjFo1YMQdN73bWkTWdlyHwfqFxJNaLbvdZJlDY7tM/kqOylhuxz
TxdFo0rdhyEFSxvKY+sc26cppwJp6pvKU4M1ctpK5wz88U2mALTSAQ33DYo8eIgIjuACYCbD4gAC
mCZjJlTKQpjH8lPIfQT/AEGsPqXdUXEnTfqWMEJqg5Kz/qA1AWeQpOm/TJhOINO5RzFaotKP+8yR
jYjd6ZjXYZzNwLOalmsfOSyLyeim0PW5xyo5SagPR1HPcn6m9OGlvNWLs0dO/UN099aeUKQeJ0p2
S4WODy5ieVazDyJgr5fYfJ0TFUhoTIOJ63OmsUTXGcHdGcTdXNPJc/hZrIxskAI2UunP1DcfYkU1
MZZ0d6oaniB+mWdlss3nEd8joFqymZEiLKz2yblIdFzCxlgfyLJOPs1rTjY+eeSkb9gfvDSrAqwe
HEhIQRBYgbbl3DY3ISlMUxyj/wAMQDF8TJqFU4eZCAf0DQP20vW7oWojRc4wZrOz5Q6hnnS1JU3H
MbecxX6qUp1mPFtsKrFYjkgmbXKw42zIVedxjzGtqMiR9MSiUfQ7PYZKbtt5lX7kC6SGA4bhtt2/
L6bgBgD+hASiUew7egGB6zSOQ9FfUJ0C9ZNfEVvzvpn0z0PMeC9TkFj+NQm7zg2qZQiZ9hE54qUa
u7bFKm2Tuc5G2yacGi41vCwbapSszDlvLOeigF8nesljHqa+4H0Q5g1HGQoOgbB2dzVXANGyC8aN
oWmnfg+JS8v5SW5lgYOx3fM0bjO6ZCVXcKVeh1GCrNbmLDPQ9JdXCVDcppeoXW/x71jNVOVOolfb
m26W8Iw1PSmoh7mu/wBenNEMnphd1S9HxYzxhjaxzkzT4NumDGkyMujD12HutbpoXCNywso8slqh
LaC6i/K1Ra52pWitn7KlHsthNTmUqqovJtKopMvlq23kTqqKGF6lCqMU3JiqKFUWKdb5jnOfYLYb
GOQ4mSIBxAob8kvmAoCYoAIkEBLuY4lT4m8FPk+E/IihyHBvD7XvI2Vck9GTS8+yk8lZYlVkcr43
xvOTbt4+k5TFGPMlWOq01mo4fKqnCPpYRsljWus2opsYms0mGh2bZsjH/CQL69wloG1adR3QO609
aSchVar2RPJlZv17oNumJCsxecafTYufkI3GoWNqm6jWT4l8NT7hCsbM1b1x9YqvCPJKwV4kUR4q
ClrUnppzto9zLctPepPG05ijMNAcs21sps4pFSCrY0g0ayca+YzcG9l6/Yq/MRTlrIRM9XZiZgJZ
FQjyLfuWxyH9BCyapdSlyxZAYNuGoXOFqwlU045KqYcsuWcgz+Ka0SIAPuhOCx3MWB/UYlGLKJvu
9vHxbdNsp+j8Lw9Bgdc5Dm8NwKG4lAw9yAYeYpgUoFTApTmNt8aaZTGMc4EIQxSEDiRgKJhEBHbv
+YAAfTlx/mIb/p2/b57cR8yA2s9rbrig9W/S1xhjp+4iWuU9G5kdOd6ho1lHw5DU6AaHf4VtqURH
gUCMZrGykfXZCwvilfWy9Um8zb86zxyssqBIChRNxDbkHIOQCYSgAAYDAbsUQMJTFLsUQDf/AEBO
fMFtHulejrrcsWu7IevDCWGshagMJ5yq+NFbIbEdYk73ZMQ2rGeLIDHEtG2mkVhrJ2xrTnkBj6Pt
yN6RiXFTj301JQ8xJRDwkajKgF5NwM1XJFzDT0XIw0qyVO3eRsswdRb9mumYSqIuWT9Fu6bqJmKY
FCrIpmKP6vQUsyZi+IgXfbfschu24hvuUwhsPHkXv5J/i/tmKYQ7FIBP3eRB3Dt9eO4lOXjsOygA
PIpT8Q47778ybhvq9u51Q23TM171+YyLPrxOmfUG1jMPaghOZUYqtMHkkRSh5gdN03Lcqg4rs7kz
qYcC3fPGWNbFkhGHj3cs8Ztjg4H9BJVIKnEvcAEdjCBuJgLsIjsIeWxjAUpuJkzf0cO3oKDOVmDs
sS6g7NCxlihHyQtn8POMG83HvmyhBQUQes5MjpB2kqU6nyKOC8viNwP4cy+gC89yj0FNIhtImW9e
ulbF1Q075owQxjrpkCoYrho+pYqzDjo8zDQdmF/QIpuxq9RvtVZvTXaNuVLZxLi1It7PXrnD22Ym
4G1VUFuy5OAl7iYTchAeAFIYvMxQMnt48REo7fHyT/yfuYhAi3MUpgE3YOROQgURMBeXnw4qonMc
5BMmKXMpVCnOPMgkKcgf/9k=""")
