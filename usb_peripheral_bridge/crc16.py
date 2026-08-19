def update(crc, data):

    crc ^= data << 8

    for _ in range(8):

        if crc & 0x8000:
            crc = ((crc << 1) ^ 0x1021) & 0xffff
        else:
            crc = (crc << 1) & 0xffff

    return crc



def calculate(data):

    crc = 0xffff

    for b in data:
        crc = update(crc, b)

    return crc
    
