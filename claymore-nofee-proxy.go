package main
import(
    "os"
    "fmt"
    "log"
    "net"
    "strings"
    "sync/atomic"
    "encoding/json"
)

var lock_account = ""
var local_port = ""
var remote_address = ""
var remote_port = ""

var conn_num int32 = 0

func main() {
    if len(os.Args) < 5 {
        fmt.Println("Usage: ./proxy [localport] [remotehost] [remoteport] [ETH Wallet]")
        fmt.Println("Example: ./proxy 9999 eth.realpool.org 9999 0x...")
        return
    }
    local_port = os.Args[1]
    remote_address = os.Args[2]
    remote_port = os.Args[3]
    lock_account = os.Args[4]

    log.Println("Wallet set:", lock_account)

    l, err := net.Listen("tcp", ":" + local_port)
    if err != nil {
        log.Fatal("Listen error:", err)
    }
    log.Println("Start proxy at port:", local_port)
    // Loop forever
    for {
        c, err := l.Accept()
        if err != nil {
            log.Println("Accept error:", err)
            continue
        }
        create_proxy(c)
    }
}

func create_proxy(client net.Conn) {
    server, err := net.Dial("tcp", remote_address + ":" + remote_port)
    if err != nil {
        log.Println("Connect to pool error:", err)
        // Close the exist socket
        client.Close()
        return
    }
    atomic.AddInt32(&conn_num, 1)
    log.Println("New connection:", client.RemoteAddr(), " Connection number:", atomic.LoadInt32(&conn_num))
    go handle_conn(client, server, true)
    go handle_conn(server, client, false)
}

func handle_conn(c1, c2 net.Conn, local2server bool) {
    var map_result map[string] interface {}
    buf := make([]byte, 512)
    defer c2.Close()
    defer c1.Close()
    if local2server {
        // Reduce connection number
        defer atomic.AddInt32(&conn_num, -1);
        defer log.Println("Close connection:", c1.RemoteAddr())
    }
    for {
        data_len, err := c1.Read(buf)
        data := buf
        if err != nil {
            // Reduce error log, this case should be client close the socket
            if  err_str := err.Error(); strings.Contains(err_str, "EOF") || strings.Contains(err_str, "use of closed network connection") {
                return
            }
            log.Println("Read error:", err)
            return
        }
        if local2server {
            err = json.Unmarshal(buf[:data_len], &map_result)
            if err != nil {
                // Garbage data, not from claymore
                log.Println("Decode error:", err)
                return
            }
            // Submit eth address
            if v, ok := map_result["method"]; ok && v == "eth_submitLogin" {
                auth_count := map_result["params"].([]interface{})[0].(string)
                log.Println("[*]Auth account:", auth_count)
                if auth_count != lock_account {
                    log.Println("[-]Devfee detected")
                    log.Println("[+]OLD", auth_count)
                    log.Println("[+]NEW", lock_account)
                    buf_str := string(buf[:data_len])
                    data = []byte(strings.Replace(buf_str, auth_count, lock_account, 1))
                    data_len = len(data)
                }
            }
        }
        _, err = c2.Write(data[:data_len])
        if err != nil {
            log.Println("Write error:", err)
            return
        }
    }
}

