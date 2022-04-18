
var b = "D5QRUmox/Uep83h8iKZIqw==";


java.nio.ByteBuffer

function fromBase64(encodedString) {
    var bytes = atob(encodedString);
    var result = bytes
        .map(function (b) { return ('00' + b.toString(16)).slice(-2); })
        .join('')
        .replace(/(.{8})(.{4})(.{4})(.{4})(.{12})/, '$1-$2-$3-$4-$5');
    return result;
}

result = fromBase64(b);
console.log(result);
