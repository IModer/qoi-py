import qoi as q
from sys import argv
from PIL import Image

def getColorspace(p):
    pass

def getMode(m):
    if m == "RGBA":
        return 4
    elif m == "RGB":
        return 3
    else:
        return 0

def main():
    filepath = ""
    outpath  = ""

    p_mode = 'enc'

    if p_mode == 'enc':

        #Open file
        try:
            f = Image.open(filepath)
        except FileNotFoundError:
            print("The file {} could not be found".format(filepath))
            exit()
        except:
            print("The file {} could not be opened".format(filepath))
            exit()

        #colorspace = getColorspace(f)

        mode = getMode(f.mode)

        w, h = f.size
        #                    colorspace hardcoded
        desc = q.qoi_desc(w, h, mode, 1)

        data = f.tobytes()

        w = q.qoi_encode(data, desc)

        f.close()

        with open(outpath, "wb+") as f:
            f.write(w)

    elif p_mode == 'dec':

        try:
            f = open(filepath, "rb+")
        except FileNotFoundError:
            print("The file {} could not be found".format(filepath))
            exit()
        except:
            print("The file {} could not be opened".format(filepath))
            exit()

        data = f.read()
        
        w = q.qoi_decode(data, len(data), 0)

        f.close()

        with open(outpath, "wb+") as f:
            f.write(w)

if __name__ == "__main__":
    main()