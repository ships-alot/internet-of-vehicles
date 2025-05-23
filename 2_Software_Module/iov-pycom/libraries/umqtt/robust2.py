from utime import ticks_ms, ticks_diff
from . import simple2


class MQTTClient(simple2.MQTTClient):
    DEBUG = False
    KEEP_QOS0 = True
    NO_QUEUE_DUPS = True
    MSG_QUEUE_MAX = 5
    RESUBSCRIBE = True

    def __init__(A, *B, **C):
        super().__init__(*B, **C)
        A.subs = []
        A.msg_to_send = []
        A.sub_to_send = []
        A.msg_to_confirm = {}
        A.sub_to_confirm = {}
        A.conn_issue = None

    def is_keepalive(A):
        B = ticks_diff(ticks_ms(), A.last_cpacket) // 1000
        if 0 < A.keepalive < B:
            A.conn_issue = simple2.MQTTException(7), 9
            return False
        return True

    def set_callback_status(A, f):
        A._cbstat = f

    def cbstat(A, pid, stat):
        E = stat
        C = pid
        try:
            A._cbstat(C, E)
        except AttributeError:
            pass
        for (D, B) in A.msg_to_confirm.items():
            if C in B:
                if E == 0:
                    A.msg_to_send.insert(0, D)
                B.remove(C)
                if not B:
                    A.msg_to_confirm.pop(D)
                return
        for (D, B) in A.sub_to_confirm.items():
            if C in B:
                if E == 0:
                    A.sub_to_send.append(D)
                B.remove(C)
                if not B:
                    A.sub_to_confirm.pop(D)

    def connect(A, clean_session=True):
        print("connection")
        B = clean_session
        if B:
            A.msg_to_send[:] = []
            A.msg_to_confirm.clear()
        try:
            C = super().connect(B)
            A.conn_issue = None
            return C
        except (OSError, simple2.MQTTException) as D:
            A.conn_issue = D, 1

    def log(A):
        if A.DEBUG:
            if type(A.conn_issue) is tuple:
                B, C = A.conn_issue
            else:
                B = A.conn_issue
                C = 0
            D = (
                "?",
                "connect",
                "publish",
                "subscribe",
                "reconnect",
                "sendqueue",
                "disconnect",
                "ping",
                "wait_msg",
                "keepalive",
                "check_msg",
            )
            print("MQTT (%s): %r" % (D[C], B))

    def reconnect(A):
        try:
            B = super().connect(False)
            A.conn_issue = None
            return B
        except (OSError, simple2.MQTTException) as C:
            A.conn_issue = C, 4
            if A.sock:
                A.sock.close()
                A.sock = None

    def resubscribe(A):
        for (B, C) in A.subs:
            A.subscribe(B, C, False)

    def add_msg_to_send(A, data):
        A.msg_to_send.append(data)
        if len(A.msg_to_send) + len(A.msg_to_confirm) > A.MSG_QUEUE_MAX:
            A.msg_to_send.pop(0)

    def disconnect(A):
        try:
            return super().disconnect()
        except (OSError, simple2.MQTTException) as B:
            A.conn_issue = B, 6

    def ping(A):
        if not A.is_keepalive():
            return
        try:
            return super().ping()
        except (OSError, simple2.MQTTException) as B:
            A.conn_issue = B, 7

    def publish(A, topic, msg, retain=False, qos=0):
        E = topic
        C = retain
        B = qos
        D = E, msg, C, B
        if C:
            A.msg_to_send[:] = [B for B in A.msg_to_send if not (E == B[0] and C == B[2])]
        try:
            F = super().publish(E, msg, C, B, False)
            if B == 1:
                A.msg_to_confirm.setdefault(D, []).append(F)
            return F
        except (OSError, simple2.MQTTException) as G:
            A.conn_issue = G, 2
            if A.NO_QUEUE_DUPS:
                if D in A.msg_to_send:
                    return
            if A.KEEP_QOS0 and B == 0:
                A.add_msg_to_send(D)
            elif B == 1:
                A.add_msg_to_send(D)

    def subscribe(A, topic, qos=0, resubscribe=True):
        B = topic
        C = B, qos
        if A.RESUBSCRIBE and resubscribe:
            if B not in dict(A.subs):
                A.subs.append(C)
        A.sub_to_send[:] = [C for C in A.sub_to_send if B != C[0]]
        try:
            D = super().subscribe(B, qos)
            A.sub_to_confirm.setdefault(C, []).append(D)
            return D
        except (OSError, simple2.MQTTException) as E:
            A.conn_issue = E, 3
            if A.NO_QUEUE_DUPS:
                if C in A.sub_to_send:
                    return
            A.sub_to_send.append(C)

    def send_queue(A):
        D = []
        for B in A.msg_to_send:
            E, I, J, C = B
            try:
                F = super().publish(E, I, J, C, False)
                if C == 1:
                    A.msg_to_confirm.setdefault(B, []).append(F)
                D.append(B)
            except (OSError, simple2.MQTTException) as G:
                A.conn_issue = G, 5
                return False
        A.msg_to_send[:] = [B for B in A.msg_to_send if B not in D]
        del D
        H = []
        for B in A.sub_to_send:
            E, C = B
            try:
                F = super().subscribe(E, C)
                A.sub_to_confirm.setdefault(B, []).append(F)
                H.append(B)
            except (OSError, simple2.MQTTException) as G:
                A.conn_issue = G, 5
                return False
        A.sub_to_send[:] = [B for B in A.sub_to_send if B not in H]
        return True

    def is_conn_issue(A):
        A.is_keepalive()
        if A.conn_issue:
            A.log()
        return bool(A.conn_issue)

    def wait_msg(A):
        A.is_keepalive()
        try:
            return super().wait_msg()
        except (OSError, simple2.MQTTException) as B:
            A.conn_issue = B, 8

    def check_msg(A):
        A.is_keepalive()
        try:
            return super().check_msg()
        except (OSError, simple2.MQTTException) as B:
            A.conn_issue = B, 10
