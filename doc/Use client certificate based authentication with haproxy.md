# Use client certificate based authentication with haproxy

This is short tutorial to show  client certificate based authentication  usage together with haproxy. 

## Create server certificate
We create a new self-signed server certifcate to sign our client certificates later.

```openssl req -new > server.cert.csr ```

 * Country name : *DE*
 * State or province name: *Nordrhein-Westfalen*
 * Organization name : *Universitaet Bielefeld*

```openssl rsa -in privkey.pem -out server.cert.key```

``` openssl x509 -in server.cert.csr -out server.cert.crt  -req -signkey server.cert.key -days 365 ```



##Create client certificate
After creating a self-signed cerver certificate, we create a client certificate and sign it with the server certificate.

Before we start we have to do some prerequites, depending on openssl configuration this may be different on your system. The following works using OSX with  an openssl macports setup, but should also work on any linux based system.

``` mkdir -p demoCA/newcerts
touch demoCA/index.txt
echo 1001 > demoCA/serial 
```
Create your private key ...


``` openssl genrsa -des3 -out jkrueger.key```

...  and the certificate request ...

``` openssl req -new -key jkrueger.key -out jkrueger.req ```
 
 * Country Name: *DE*
 * State or Province Name: *Nordrhein-Westfalen*
 * Organization Name : *Universitaet Bielefeld*
 
... and sign with our previously generated server certificate.

```openssl ca -cert server.cert.crt -keyfile server.cert.key -out jkrueger.crt -in jkrueger.req```

## HAProxy configuration

```
...
bind YOUR_SERVER_IP:443 ssl crt YOUR_SERVER_CERT ca-file YOUR_SELF_SIGNED_SERVER_CERT verify optional
  http-request set-header X-SSL-Client-Verify    %[ssl_c_verify]                                                                           │root@openstack030:/etc/haproxy# ll
  http-request set-header X-SSL-Client-DN        %{+Q}[ssl_c_s_dn]                                                                         │total 72
  http-request set-header X-SSL-Client-CN        %{+Q}[ssl_c_s_dn(cn)]                                                                     │drwxr-xr-x   3 root    root  4096 Nov 30 09:41 ./
  http-request set-header X-SSL-Issuer           %{+Q}[ssl_c_i_dn]                                                                         │drwxr-xr-x 120 root    root 12288 Nov 23 11:03 ../
  http-request set-header X-SSL-Client-NotBefore %{+Q}[ssl_c_notbefore]                                                                    │lrwxrwxrwx   1 root    root    10 Nov 30 09:41 client-ca.pem -> elixir.pem
  http-request set-header X-SSL-Client-NotAfter  %{+Q}[ssl_c_notafter]
...
```

With http-request set-header directive haproxy add (and possible overwrite) some additional http header for cleint 


## Example request using curl
The easiest way to use our client certificate is to pass a combined key - certifcate file in pem format to curl. Generating a combined key - certificate file is quite simple, just cat the key and the certificate into one file:

```
cat jkrueger.key jkrueger.crt > jkrueger.pem
```

The curl request is then straightforward ... 

```
curl --cert jkrueger.pem https://YOUR_SERVER
```