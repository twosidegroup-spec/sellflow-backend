import 'dart:io';
import 'dart:convert';

Future<void> main() async {
  final server = await HttpServer.bind('127.0.0.1', 3000);
  print('Proxy running on http://127.0.0.1:3000');
  
  await for (final request in server) {
    print('Proxy received request: ${request.method} ${request.uri.path}');
    
    request.response
      ..statusCode = HttpStatus.ok
      ..headers.contentType = ContentType.json
      ..headers['Access-Control-Allow-Origin'] = '*'
      ..headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
      ..headers['Access-Control-Allow-Headers'] = '*'
      ..write('{"status":"proxy running"}');
    await request.response.close();
  }
}
