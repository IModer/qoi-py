#from math import log2

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

# def QOI_COLOR_HASH(C):
#     (r,g,b,a) = C
#     return (ungroup(r)*3 + ungroup(g)*5 + ungroup(b)*7 + ungroup(a)*11)


# def group(n, b):
#     if b == -1:
#         b = round(log2(n) / 8)
#     a = list(map(int, list(str(bin(n))[2:])))
#     return [0 for x in range((b * 8) - len(a))] + a

# def ungroup(l):
#     a = ""
#     for x in l:
#         a += str(x)
#     if a == '':
#         return 0
#     return int(a, 2)

# def qoi_write_n(bytes, p, n, v):
#     #write n bit from v to bytes
#     #return the opostition in bytes (p)
#     bytes[p:p+n] = v
    
#     return p+n

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

# def qoi_read_n(bytes, p, n):
#     #read 32 bits from bytes
#     #return the bits and the position in bytes (p)
#     a = bytes[p:p+n];
#     return (a, p+n)

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
    #bytes = [0 for _ in range(maxsize)]

    #index is a 64 long list of bytes
    
    index = [(0,0,0,0) for _  in range(64)]
    #index = [0 for _ in range(64 * 8)]

    #writer the desc header to bytes

    qoi_write_32(bytes, QOI_MAGIC)   #4 bytes
    qoi_write_32(bytes, desc.width)
    qoi_write_32(bytes, desc.height)
    bytes.append(desc.channels)
    bytes.append(desc.colorspace)    #1 byte
    # p = qoi_write_n(bytes, p, 32, group(QOI_MAGIC, 4))
    # p = qoi_write_n(bytes, p, 32, group(desc.width, 4))
    # p = qoi_write_n(bytes, p, 32, group(desc.height, 4))
    # p = qoi_write_n(bytes, p, 8,  group(desc.channels, 1))
    # p = qoi_write_n(bytes, p, 8,  group(desc.colorspace, 1))

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

            # px = (pixels[px_pos:px_pos+8], 
            #       pixels[px_pos+8:px_pos+8*2],
            #       pixels[px_pos+8*2:px_pos+8*3],
            #       pixels[px_pos+8*3:px_pos+8*4])
        else:
            # we read 3 bytes

            px = (pixels[px_pos  ],
                  pixels[px_pos+1],
                  pixels[px_pos+2],
                  255)

            # px = (pixels[px_pos:px_pos+8], 
            #       pixels[px_pos+8:px_pos+8*2],
            #       pixels[px_pos+8*2:px_pos+8*3],
            #       255)

        #Method 1: runs
        # if current px and prev px are the same we record a QOI_OP_RUN
        if px == px_prev:
            run += 1
            if (run == 62 or px_pos == px_end):

                bytes.append(QOI_OP_RUN | (run-1))
                #p = qoi_write_n(bytes, p, 8, group(QOI_OP_RUN | (run-1), 1))
                run = 0
        else:
            #Method 2: index
            # if the current pixel has been recoded in index, then we record a QOI_OP_INDEX
            
            # If we are in a run then close it and record a QOI_OP_RUN
            if (run > 0):

                bytes.append(QOI_OP_RUN | (run-1))
                #p = qoi_write_n(bytes, p, 8, group(QOI_OP_RUN | (run-1), 1))
                run = 0
            
            index_pos = QOI_COLOR_HASH(px) % 64

            # We read the pixel from the index

            

            # px_ind = (index[index_pos:index_pos+8], 
            #          index[index_pos+8:index_pos+8*2],
            #          index[index_pos+8*2:index_pos+8*3],
            #          index[index_pos+8*3:index_pos+8*4])
            

            if (index[index_pos] == px):

                bytes.append(QOI_OP_INDEX | index_pos)
                #p = qoi_write_n(bytes, p, 8, group(QOI_OP_INDEX | index_pos, 1))
            else:
                # Method 3: color diff
                # if we can record the color diff of prev px and curr px then we do
                # and record a QOI_OP_DIFF

                #save px to index

                index[index_pos] = px

                # (r, g, b, a) = px
                # index[index_pos:index_pos+8]       = r
                # index[index_pos+8:index_pos+8*2]   = g
                # index[index_pos+8*2:index_pos+8*3] = b
                # index[index_pos+8*3:index_pos+8*4] = a

                # if the alpha channels match then we try to record the diff
                if (px[3] == px_prev[3]):
                    
                    vr = px[0] - px_prev[0]
                    vg = px[1] - px_prev[1]
                    vb = px[2] - px_prev[2]
                    
                    # vr = ungroup(r) - ungroup(px_prev[0])
                    # vg = ungroup(g) - ungroup(px_prev[1])
                    # vb = ungroup(b) - ungroup(px_prev[2])

                    vg_r = vr - vg
                    vg_b = vb - vg
                    
                    # Normal DIFF
                    if (vr > -3 and vr < 2 and 
                        vg > -3 and vg < 2 and
                        vb > -3 and vb < 2):

                        towrite = QOI_OP_DIFF | (vr + 2) << 4 | (vg + 2) << 2 | (vb + 2)
                        
                        bytes.append(towrite)
                        #p = qoi_write_n(bytes, p, 8, group(towrite, 1))
                    # Luma DIFF
                    elif (vg_r >  -9 and vg_r <  8 and
                          vg   > -33 and vg   < 32 and
                          vg_b >  -9 and vg_b <  8):
                        
                        bytes.append(QOI_OP_LUMA     | (vg   + 32))
                        bytes.append((vg_r + 8) << 4 | (vg_b + 8))
                        #p = qoi_write_n(bytes, p, 8, group(QOI_OP_LUMA     | (vg   + 32), 1))
                        #p = qoi_write_n(bytes, p, 8, group((vg_r + 8) << 4 | (vg_b +  8), 1))
                    
                    # NORMAL RGB
                    else:
                        
                        bytes.append(QOI_OP_RGB)
                        bytes.append(px[0])
                        bytes.append(px[1])
                        bytes.append(px[2])
                        
                        # p = qoi_write_n(bytes, p, 8, group(QOI_OP_RGB, 1))
                        # p = qoi_write_n(bytes, p, 8, r)
                        # p = qoi_write_n(bytes, p, 8, g)
                        # p = qoi_write_n(bytes, p, 8, b)
                # NORMAL RGBA
                else:
                    
                    bytes.append(QOI_OP_RGBA)
                    bytes.append(px[0])
                    bytes.append(px[1])
                    bytes.append(px[2])
                    bytes.append(px[3])
                    
                    # p = qoi_write_n(bytes, p, 8, group(QOI_OP_RGBA, 1))
                    # p = qoi_write_n(bytes, p, 8, r)
                    # p = qoi_write_n(bytes, p, 8, g)
                    # p = qoi_write_n(bytes, p, 8, b)
                    # p = qoi_write_n(bytes, p, 8, a)
        
        px_prev = px
        px_pos += channels

    #padding
    for x in qoi_padding:
        bytes.append(x)

        #p = qoi_write_n(bytes, p, 8, group(x,1))

    return bytes

def qoi_decode(data, size: int, desc: qoi_desc, channels: int) -> None:
    pass

def main():

    with open("../images/test2.bin", "rb+") as f:
        bytes = f.read()

    data = bytes

    # for b in bytes:
    #     data += group(b, 1)
    
    #print(data)
    # (qoi_data, len_in_bits) = qoi_encode(data, qoi_desc(153,153,4,0))

    # len_in_bytes = int(len_in_bits / 8)

    # w = bytearray(len_in_bytes)

    # for x in range(len_in_bytes):
    #     w[x] = ungroup(qoi_data[x*8:(x+1)*8])

    w = qoi_encode(data, qoi_desc(628,655,3,0))

    with open("../images/out_test2.qoi", "wb+") as f:
        f.write(w)

if __name__ == "__main__":
    main()