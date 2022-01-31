###CONSTANTS###
QOI_SRGB   = 0
QOI_LINEAR = 1

QOI_OP_INDEX =  0x00 # 00xxxxxx
QOI_OP_DIFF  =  0x40 # 01xxxxxx
QOI_OP_LUMA  =  0x80 # 10xxxxxx
QOI_OP_RUN   =  0xc0 # 11xxxxxx
QOI_OP_RGB   =  0xfe # 11111110
QOI_OP_RGBA  =  0xff # 11111111

QOI_MASK_2   =  0xc0 # 11000000

QOI_MAGIC = 1903126886 # Magic...
QOI_HEADER_SIZE = 14
QOI_PIXELS_MAX = 400000000
qoi_padding = [0,0,0,0,0,0,0,1]

def QOI_COLOR_HASH(C: tuple):
    (r,g,b,a) = C
    return (r*3 + g*5 + b*7 + a*11)

def qoi_write_32(bytes: bytearray, v: int):
    #write 4 bytes from v to bytes
    #return the opostition in bytes (p)
    i = len(bytes)
    bytes.append(0)
    bytes.append(0)
    bytes.append(0)
    bytes.append(0)
    bytes[i  ] = (0xff000000 & v) >> 24
    bytes[i+1] = (0x00ff0000 & v) >> 16
    bytes[i+2] = (0x0000ff00 & v) >>  8
    bytes[i+3] = (0x000000ff & v)

class qoi_desc():
    def __init__(self, width: int, height: int,  channels: int , colorspace: int) -> None:
        self.width      = width
        self.height     = height
        self.channels   = channels
        self.colorspace = colorspace

def qoi_encode(data: bytearray, desc: qoi_desc) -> bytearray:

    #if the image is invalid then we return with None
    if (data == None or desc == None or
        desc.width == 0 or desc.height == 0 or
        desc.channels < 3 or desc.channels > 4 or
        desc.colorspace > 1 or
        desc.height >= QOI_PIXELS_MAX / desc.width):
        return None

    maxsize = desc.width * desc.height * (desc.channels + 1) + QOI_HEADER_SIZE + len(qoi_padding)

    p = 0

    #bytes and index 
    #bytes is a maxsize long list of bits,
    #this is where the converted image will be 

    bytes = bytearray()

    #index is a 64 long list of bytes
    
    index = [(0,0,0,0) for _  in range(64)]

    #writer the desc header to bytes

    qoi_write_32(bytes, QOI_MAGIC)   #4 bytes
    qoi_write_32(bytes, desc.width)
    qoi_write_32(bytes, desc.height)
    bytes.append(desc.channels)
    bytes.append(desc.colorspace)    #1 byte

    pixels = data  # bytearray()

    run = 0

    px_prev = (0,0,0,255)

    px = px_prev

    px_len   = desc.width * desc.height * desc.channels
    px_end   = px_len - desc.channels
    channels = desc.channels

    px_pos = 0

    while(px_pos < px_len):

        #if we have 4 channels or 3
        if (channels == 4):
            # we read 4 bytes (4 8 bit chunks)

            px = (pixels[px_pos  ],
                  pixels[px_pos+1],
                  pixels[px_pos+2],
                  pixels[px_pos+3])
        else:
            # we read 3 bytes

            px = (pixels[px_pos  ],
                  pixels[px_pos+1],
                  pixels[px_pos+2],
                  255)

        #Method 1: runs
        # if current px and prev px are the same we record a QOI_OP_RUN
        if px == px_prev:
            run += 1
            if (run == 62 or px_pos == px_end):

                bytes.append(QOI_OP_RUN | (run-1))
                run = 0
        else:
            #Method 2: index
            # if the current pixel has been recoded in index, then we record a QOI_OP_INDEX
            
            # If we are in a run then close it and record a QOI_OP_RUN
            if (run > 0):

                bytes.append(QOI_OP_RUN | (run-1))
                run = 0
            
            index_pos = QOI_COLOR_HASH(px) % 64
            

            if (index[index_pos] == px):

                bytes.append(QOI_OP_INDEX | index_pos)
            else:
                # Method 3: color diff
                # if we can record the color diff of prev px and curr px then we do
                # and record a QOI_OP_DIFF

                #save px to index

                index[index_pos] = px

                # if the alpha channels match then we try to record the diff
                if (px[3] == px_prev[3]):
                    
                    vr = px[0] - px_prev[0]
                    vg = px[1] - px_prev[1]
                    vb = px[2] - px_prev[2]

                    vg_r = vr - vg
                    vg_b = vb - vg
                    
                    # Normal DIFF
                    if (vr > -3 and vr < 2 and 
                        vg > -3 and vg < 2 and
                        vb > -3 and vb < 2):

                        towrite = QOI_OP_DIFF | (vr + 2) << 4 | (vg + 2) << 2 | (vb + 2)
                        
                        bytes.append(towrite)
                    # Luma DIFF
                    elif (vg_r >  -9 and vg_r <  8 and
                          vg   > -33 and vg   < 32 and
                          vg_b >  -9 and vg_b <  8):
                        
                        bytes.append(QOI_OP_LUMA     | (vg   + 32))
                        bytes.append((vg_r + 8) << 4 | (vg_b + 8))
                    
                    # NORMAL RGB
                    else:
                        
                        bytes.append(QOI_OP_RGB)
                        bytes.append(px[0])
                        bytes.append(px[1])
                        bytes.append(px[2])
                        
                # NORMAL RGBA
                else:
                    
                    bytes.append(QOI_OP_RGBA)
                    bytes.append(px[0])
                    bytes.append(px[1])
                    bytes.append(px[2])
                    bytes.append(px[3])
        
        px_prev = px
        px_pos += channels

    #padding
    for x in qoi_padding:
        bytes.append(x)

    return bytes

def bti(b: bytearray) -> int:
    return int(b.hex(), 16)

def qoi_decode(data: bytearray, size: int, channels: int) -> bytearray:
    # read the desc from data
    # desc is the first 14 bytes

    p = 4
    desc = qoi_desc(
        bti(data[p:p+4]),
        bti(data[p+4:p+8]),
        data[p+8],
        data[p+9]
    )
    p = 14


    if (data == None or (channels != 0 and channels != 3 and channels != 4) or
        size < QOI_HEADER_SIZE + len(qoi_padding) or 
        desc.width == 0 or desc.height == 0 or
        desc.channels < 3 or desc.channels > 4 or
        desc.colorspace > 1 or
        data[0:4] != b'qoif' or
        desc.height >= QOI_PIXELS_MAX / desc.width):
        return None

    index = [(0,0,0,0) for _  in range(64)]
    px = (0,0,0,255)
    run = 0
    bytes = data

    if (channels == 0):
        channels = desc.channels

    px_len = desc.width * desc.height * channels;
    pixels = bytearray(px_len)

    chunks_len = size - len(qoi_padding);

    px_pos = 0
    while(px_pos < px_len):
        if (run > 0):
            run -= 1
        elif (p < chunks_len):
            b1 = bytes[p]
            p += 1

            #QOI_OP_RGB
            if b1 == QOI_OP_RGB:
                r = bytes[p]
                p += 1
                g = bytes[p]
                p += 1
                b = bytes[p]
                p += 1
                px = (r,g,b,255)
            elif b1 == QOI_OP_RGBA:
                r = bytes[p]
                p += 1
                g = bytes[p]
                p += 1
                b = bytes[p]
                p += 1
                a = bytes[p]
                p += 1
                px = (r,g,b,a)
            elif ((b1 & QOI_MASK_2) == QOI_OP_INDEX):
                px = index[b1]
            elif ((b1 & QOI_MASK_2) == QOI_OP_DIFF):
                (r,g,b,a) = px

                r = (r + ((b1 >> 4) & 0x03) - 2) % 256
                g = (g + ((b1 >> 2) & 0x03) - 2) % 256
                b = (b + ( b1       & 0x03) - 2) % 256

                px = (r,g,b,a)
            elif ((b1 & QOI_MASK_2) == QOI_OP_LUMA):
                b2 = bytes[p]
                p += 1

                (r,g,b,a) = px

                vg = (b1 & 0x3f) - 32
                r = (r + vg - 8 + ((b2 >> 4) & 0x0f)) % 256
                g = (g + vg                         ) % 256
                b = (b + vg - 8 +  (b2       & 0x0f)) % 256

                px = (r,g,b,a)

            elif ((b1 & QOI_MASK_2) == QOI_OP_RUN):
                run = (b1 & 0x3f)
            
            index[QOI_COLOR_HASH(px) % 64] = px
                

        (r,g,b,a) = px
        if (channels == 4):
            pixels[px_pos + 0] = r
            pixels[px_pos + 1] = g
            pixels[px_pos + 2] = b
            pixels[px_pos + 3] = a
        else:
            pixels[px_pos + 0] = r
            pixels[px_pos + 1] = g
            pixels[px_pos + 2] = b

        px_pos += channels
    
    return pixels

def main():

    filepath = ""
    outpath  = ""

    with open(filepath, "rb+") as f:
        bytes = f.read()

    data = bytes

    w = qoi_encode(data, qoi_desc(628,655,3,0))

    with open(outpath, "wb+") as f:
        f.write(w)

if __name__ == "__main__":
    main()