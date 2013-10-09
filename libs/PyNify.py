import sys
import httplib
import json

def tinyfy(url):
    finalurl = '{"longUrl": "' + url + '"}'
    connection = httplib.HTTPSConnection("www.googleapis.com")
    connection.request("POST","/urlshortener/v1/url",finalurl,{"Content-Type":"application/json"})
    response = connection.getresponse()
    j = json.loads(response.read())
    if j.has_key("id"):
        return j["id"]
    else:
        return "error: ",j

def main(url = None):
    print url
    if url == []:
        url = raw_input("Enter url: ")
    else:
        url = url
    result = tinyfy(url)
    print "Your link is: " + result

if __name__ == '__main__':
    main(sys.argv[1:])