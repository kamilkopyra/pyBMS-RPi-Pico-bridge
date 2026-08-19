//  This script enables communication between a Raspberry Pi Pico 2 and an
//  Analog Devices Battery Management System (BMS) using the pyBMS library.
// 
//  The Pico acts as a USB-to-SPI bridge between the host PC and the BMS device,
//  allowing configuration, measurement acquisition, and status monitoring.
// 
//  Although the Pico cannot connect directly to the ADBMS GUI software,
//  data visualization is still possible using the Customer_GUI.py script
//  provided by Analog Devices as part of the pyBMS framework.
// 
//  This script was written to replace the SDP-K1 evaluation board 
//  in the original Analog Devices measurement chain.
//  The original goal was to emulate the Linduino platform. 
//  However, due to the limited amount of Linduino-related
//  documentation and implementation details available within the pyBMS
//  library, SDP-K1 compatibility was chosen as the primary reference.
//
// 
//  Communication path:
//  PC ---------> Raspberry Pi Pico 2 --------> ADBMS6822 -----------> ADBMS6832
//        USB                           SPI                 isoSPI
// 
//  Although the communication pipeline has been tested using
//  the ADBMS6822 and ADBMS6832, it should also be compatible with
//  other Analog Devices battery-monitoring devices supported by
//  the pyBMS library.
//
//  The communication pipeline supports multiple daisy-chained measurement devices.
//  Devices are defined on the PC side, and command sequences are generated
//  automatically by the pyBMS framework.
// 
//  Potential improvements:
//  - It may be possible to connect directly to the ADBMS GUI software by
//    emulating the SDP-K1 evaluation board by modifying the reported USB
//    device name and/or USB descriptors.
// 
//  - Add a standalone monitoring mode running directly on the Pico,
//     eliminating the need for a host PC during normal operation
//  
//  - Design a dedicated PCB integrating the Raspberry Pi Pico 2 and the
//    ADBMS6822 transceiver into a single compact module.

//  Examples for PC side scripts can be found in pc_tests folder 




#include "pico/stdlib.h"
#include "hardware/spi.h"
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>



#define MAX_FRAME_SIZE 256
#define MAX_COMMANDS 128
#define MAX_COMMAND_SIZE 256


uint8_t command_buffer[MAX_COMMANDS][MAX_COMMAND_SIZE];
uint16_t command_sizes[MAX_COMMANDS];
uint16_t command_orig_sizes[MAX_COMMANDS];

static uint8_t tx_dummy [MAX_COMMAND_SIZE];


uint16_t command_count = 0;

bool unsupported_type = 0;
int raw_calls = 0;


#define SCK_PIN 2
#define MOSI_PIN 3
#define MISO_PIN 4
#define CS_PIN 5
#define GPIO_PIN 6          
 
#define SPI_SPEED (0.5* 1000* 1000)
 
#define SPI_CPOL SPI_CPOL_0
#define SPI_CPHA SPI_CPHA_0
 
#define CHAIN_LENGTH 1


uint16_t execute_command(uint8_t *cmd_buf, uint16_t len);


void send_ack()
{
    uint8_t resp[] =
    {
        0x00,
        0x00,
        0x00,
        0x00,
        0x00
    };

    for(int i=0;i<5;i++)
    {
        putchar_raw(resp[i]);
    }
    fflush(stdout);
}

static inline void cs_low(void) 
{
    for (int i = 0; i < 10; i ++)
    {
        gpio_put(CS_PIN, 0);
        busy_wait_us(85);
        gpio_put(CS_PIN,1);
        busy_wait_us(85);
    }
    gpio_put(CS_PIN, 0);
    busy_wait_us(1);        // sleep_us did not work, it stops data read on USB
}

static inline void cs_high (void)
{
    busy_wait_us(1);
    gpio_put(CS_PIN, 1);
    busy_wait_us(3);
}

void send_debug(uint8_t cmd, uint32_t frame_len)
{
    uint8_t resp[] =
    {
        0x00, 0x00, 0x00, 0x08,
        cmd,
        (uint8_t)frame_len,
        0xAA,
        0x55
    };

    for(uint32_t i = 0; i < sizeof(resp); i++)
    {
        putchar_raw(resp[i]);
    }
}

void spi_write(uint8_t *tx_data, size_t tx_len)
{
    spi_write_blocking(
        spi0,
        tx_data,
        tx_len
    );
}

static void spi_write_slow(const uint8_t *data, uint16_t len, uint32_t gap_us)
{
    for (uint16_t i = 0; i < len; i++) 
    {
        spi_write_blocking(spi0, &data[i], 1);
        busy_wait_us(gap_us);
    }
}

static void spi_read_slow(uint8_t *rx, uint16_t len, uint32_t gap_us){  
// This function inserts delays between SPI bytes, matching the behavior
// observed on the Linduino implementation.
//
// The ADBMS6832 datasheet does not explicitly require these delays;
// however, during validation no valid data was received on MISO without
// introducing inter-byte gaps during read transactions. 

    uint8_t dummy = 0x00;
    for (uint16_t i = 0; i < len; i++) 
    {
        spi_write_read_blocking(spi0, &dummy, &rx[i], 1);
        busy_wait_us(gap_us);
    }
}


void add_command_to_buffer(uint8_t *frame, uint16_t len)
{
    if(command_count >= MAX_COMMANDS)
    {
        return;
    }

    memcpy(
        command_buffer[command_count],
        frame,
        len
    );

    command_sizes[command_count] = len;
    command_orig_sizes[command_count] = len;

    command_count++;

    send_ack();
}

void run_cmd(void)
{
    raw_calls += 1;
    unsupported_type = 0;
    

    for(uint16_t i = 0; i < command_count; i++) 
        {

        uint16_t orig = command_orig_sizes[i];

        uint16_t added = execute_command(
             command_buffer[i],
             orig);
         command_sizes[i] = orig + added;
        }

    if(unsupported_type)
    {
        uint8_t resp[5] = {0,0,0,0, 44};
        for (int i = 0; i < 5; i++) putchar_raw(resp[i]);
        fflush(stdout);
        return;
    }
    
    send_ack();
}

void free_run_cmd()
{
    send_ack();
}
void get_fw_ver_cmd()
{
    uint8_t resp[5] = {0,0,0,0, (uint8_t)raw_calls};
    for(int i = 0; i < 5; i++) putchar_raw(resp[i]);
    fflush(stdout);
}

void get_cmd(void)
{
    uint32_t total = 4 + 2;

    for (uint16_t i = 0; i < command_count; i++)
    {
        uint16_t payload_len = command_sizes[i] - 10;
        total += 2 + payload_len;
    }
    putchar_raw((total >> 24) & 0xFF);
    putchar_raw((total >> 16) & 0xFF);
    putchar_raw((total >> 8) & 0xFF);
    putchar_raw(total  &  0xFF);

    putchar_raw(command_count >> 8);
    putchar_raw(command_count & 0xFF);

    for(uint16_t i = 0; i < command_count; i++)
    {
        uint16_t payload_len = command_sizes[i] - 10;

        putchar_raw(payload_len >> 8);
        putchar_raw(payload_len & 0xFF);

        for(uint16_t j = 10; j < command_sizes[i]; j++)
        {
            putchar_raw(
                command_buffer[i][j]
            );
        }

    }

    fflush(stdout);

    command_count = 0;

    memset(command_sizes, 0, sizeof(command_sizes));
    memset(command_orig_sizes, 0, sizeof(command_orig_sizes));
}

void clear_cmd(void)
{
    command_count = 0;

    memset(
        command_sizes,
        0,
        sizeof(command_sizes)
    );

    memset(
        command_buffer,
        0,
        sizeof(command_buffer)
    );

    memset(command_orig_sizes, 0, sizeof(command_orig_sizes));

    send_ack();
}

void raw_cmd(void)
{
    raw_calls += 1;
    uint32_t  total = 4 + 2;
    for(uint16_t i = 0; i < command_count; i++)
    {
        total += 2+ command_sizes[i];
    }

    putchar_raw((total >> 24) & 0xFF);
    putchar_raw((total >> 16) & 0xFF);
    putchar_raw((total >> 8) & 0xFF);
    putchar_raw((total)  & 0xFF);

    putchar_raw(command_count >> 8);
    putchar_raw(command_count & 0xFF);

    for (uint16_t i = 0; i < command_count; i ++)
    {
        putchar_raw(command_sizes[i] >> 8);
        putchar_raw(command_sizes[i] & 0xFF);
        for(uint16_t j = 0; j < command_sizes[i]; j++)
            putchar_raw(command_buffer[i][j]);
    }

    fflush(stdout);

}


void get_system_command(uint8_t *frame)
{
    switch(frame[2])
    {
        case 0x01:    // run command
            run_cmd();
            break;

        case 0x02:     // get command
            get_cmd();
            break;

        case 0x03:     //  raw command
            raw_cmd();
            break;
        case 0x05:      //  clear command
            clear_cmd();
            break;
        case 0x07:     //    get firmware version
            get_fw_ver_cmd();
            break;
        case 0x08:      //    start freerun mode
            free_run_cmd();
            break;
        default:
            break;
    }
}

uint16_t execute_command(uint8_t *cmd_buf, uint16_t len)
{
    uint8_t cmd = cmd_buf[3];
    uint16_t tx_len = ((uint16_t)cmd_buf[4] << 8) | cmd_buf[5];
    uint16_t rx_len = ((uint16_t)cmd_buf[6] << 8) | cmd_buf[7];
    uint8_t *tx_data = &cmd_buf[10];

    // Command mapping reference: RaspberryPi_SPI.py
    switch(cmd)
    {

        case 0x01:   // write
        {
            cs_low();
            spi_write_slow(tx_data,tx_len, 250);
            cs_high();
            return 0;
        }

        case 0x02: // read
            
            cs_low();
            if (tx_len) {
                for(int i = 0; i < tx_len; i++)
                {
                    spi_write_slow(&tx_data[i], 1, 250);
                    busy_wait_us(70);
                }
            }
            //cs_high();

            if (rx_len) 
            {
                //cs_low();
                memset(tx_dummy, 0x00, rx_len);
                spi_read_slow(&cmd_buf[len], rx_len, 50);
                cs_high();
                return rx_len;
            }

            cs_high();
            return 0;
        
        case 0x03:   //poll
            return 0;

        case 0x04:   //delay_us
            if(tx_len >= 2)
                busy_wait_us(((uint16_t)tx_data[0] << 8) | tx_data[1]);
            return 0;

        case 0x05:   // delay_ms
            if (tx_len >= 2)
                busy_wait_ms(((uint16_t)tx_data[0] << 8) | tx_data[1]);
            return 0;

        case 0x08: // SPI_WAKEUP
            cs_low();
            if (tx_len) spi_write_blocking(spi0, tx_data, tx_len);
            cs_high();

            if(tx_len >= 2)
                busy_wait_us(((uint16_t)tx_data[0] << 8) | tx_data[1]);
            return 0;

        case 0x0E:   // set SPI frequency
            if (tx_len >= 2)
            {
                uint32_t freq_khz =
                    ((uint32_t)tx_data[0] << 8) |
                    tx_data[1];

                spi_set_baudrate(
                    spi0,
                    freq_khz * 1000
                );
            }
            return 0;
                
        
        default:
            unsupported_type = 1;
            return 0;
        }
    }






void setup() 
{
    stdio_init_all();
    busy_wait_ms(1000);    // busy_wait_ms() is used instead of sleep_ms() because sleep_ms()
                                // occasionally caused USB communication stalls during command reception.

    gpio_init(CS_PIN);
    gpio_set_dir(CS_PIN, GPIO_OUT);
    cs_high();

    gpio_set_function(SCK_PIN, GPIO_FUNC_SPI);
    gpio_set_function(MOSI_PIN, GPIO_FUNC_SPI);
    gpio_set_function(MISO_PIN, GPIO_FUNC_SPI);
 
    spi_init(spi0, SPI_SPEED);      
    spi_set_format(spi0, 8, SPI_CPOL, SPI_CPHA, SPI_MSB_FIRST);


}


int main()
{
    
    setup();

    uint8_t frame[MAX_FRAME_SIZE];

    while (true)
    {
        int b0 = getchar_timeout_us(1000);

        if (b0 == PICO_ERROR_TIMEOUT) continue;

        int b1 = getchar_timeout_us(50000);
        if(b1 < 0) continue;


        uint32_t frame_len =
            2 + (((uint32_t)b0 << 8) | (uint32_t)b1);

        if (frame_len < 3 || frame_len > MAX_FRAME_SIZE)
            continue;

        frame[0] = (uint8_t)b0;
        frame[1] = (uint8_t)b1;

        bool ok = true;

        for (uint32_t i = 2; i < frame_len; i++)
        {
            int c = getchar_timeout_us(50000);
            if (c<0) {ok = false; break;}
            frame[i] = (uint8_t)c;
        }
        
        if (!ok) continue;;

        if(frame[2] == 0x00)
            {
                add_command_to_buffer(frame, frame_len);
            }
        else
        {
            get_system_command(frame);
        }

    }
}
