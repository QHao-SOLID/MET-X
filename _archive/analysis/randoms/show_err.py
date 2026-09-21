raw = open('err.log', 'rb').read()
text = raw.decode('utf-16', errors='replace')
i = text.find('An error occurred while executing the following cell')
print(text[i:i+900] if i != -1 else text[-600:])
