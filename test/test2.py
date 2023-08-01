# test2

import pexpect,time

ins = pexpect.spawn('python3 test1.py',cwd=rf'/mnt/raid1/Amadeus/test')

print("waiting")

time.sleep(1)

print("sending")

ins.sendline("testing this shit")

print(ins.read())
