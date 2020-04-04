import requests
import progressbar
import os


def download_file_to(link, path):
    r = requests.get(link, stream=True)
    if r.status_code != 200:
        print(r.status_code, link)
        return False
    file_size = int(r.headers['Content-length'])
    print("Downloading file %s (%d bytes)" % (path, file_size))
    widgets = [
        '%s: ' % os.path.basename(path), progressbar.Percentage(),
        ' ', progressbar.Bar(marker=progressbar.AnimatedMarker(fill='#')),
        ' ', progressbar.Counter('%(value)d'), '/' + str(file_size) + ' bytes downloaded',
        ' ', progressbar.ETA(),
        ' ', progressbar.FileTransferSpeed(),
        ]
    bar = progressbar.ProgressBar(widgets=widgets, max_value=file_size,
                                  redirect_stdout=True).start()
    with open(path, "wb") as f:
        part = 8192
        for chunk in r.iter_content(part):
            bar += len(chunk)
            f.write(chunk)
    bar.finish()
    return True


def download_web_page(link):
    r = requests.get(link)
    if r.status_code != 200:
        print(r.status_code, "error")
        exit(1)
    return r.text

