import struct


class NetworkCrypto:
    HEADER_FORMAT = "!I"  # 4 בתים שמייצגים את אורך המידע
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
    XOR_KEY = 0x5A  # מפתח הצפנה סימטרי פשוט לפרויקט

    @staticmethod
    def _cipher(data_bytes):
        """הצפנה/פענוח XOR בסיסית ומהירה לביטים"""
        return bytes([b ^ NetworkCrypto.XOR_KEY for b in data_bytes])

    @staticmethod
    def send_secure_msg(sock, msg_str):
        """מצפין, אורז ושולח הודעה ברשת"""
        encrypted_data = NetworkCrypto._cipher(msg_str.encode('utf-8'))
        header = struct.pack(NetworkCrypto.HEADER_FORMAT, len(encrypted_data))
        sock.sendall(header + encrypted_data)

    @staticmethod
    def recv_secure_msg(sock):
        """קורא כותרת, קורא את התוכן ומפענח אותו"""
        try:
            header = sock.recv(NetworkCrypto.HEADER_SIZE)
            if not header:
                return None
            msg_len = struct.unpack(NetworkCrypto.HEADER_FORMAT, header)[0]

            # קריאת כל הגוף
            data = b""
            while len(data) < msg_len:
                packet = sock.recv(msg_len - len(data))
                if not packet:
                    return None
                data += packet

            return NetworkCrypto._cipher(data).decode('utf-8')
        except:
            return None