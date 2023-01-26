up_exchange = '''
static void exchange_stream(INTERFACE_WIDTH *result, hls::stream<pkt> &streaming_to, hls::stream<pkt> &streaming_from){
    int i;
    for(i = 0; i < TOP_APPEND*STAGE_COUNT; i++){
#pragma HLS pipeline II=1        
        pkt temp; 
        temp.data = result[i + GRID_COLS/WIDTH_FACTOR*PART_ROWS].range(511, 0);
        streaming_to.write(temp);  
    }
    for(i = 0; i < BOTTOM_APPEND*STAGE_COUNT; i++){
#pragma HLS pipeline II=1
        pkt temp2 = streaming_from.read();          
        result[i + GRID_COLS/PARA_FACTOR*PART_ROWS + (TOP_APPEND-BOTTOM_APPEND)*STAGE_COUNT].range(511, 0) = temp2.data;
    }
}
'''

mid_exchange = '''
static void exchange_with_up(INTERFACE_WIDTH *result, hls::stream<pkt> &streaming_to, hls::stream<pkt> &streaming_from){
    int i;
    for(i = 0; i < TOP_APPEND*STAGE_COUNT; i++){
#pragma HLS pipeline II=1
        pkt temp2 = streaming_from.read();          
        result[i].range(511, 0) = temp2.data;
    }
    for(i = 0; i < BOTTOM_APPEND*STAGE_COUNT; i++){
#pragma HLS pipeline II=1        
        pkt temp; 
        temp.data = result[i + TOP_APPEND*STAGE_COUNT].range(511, 0);
        streaming_to.write(temp);
    }
}

static void exchange_with_down(INTERFACE_WIDTH *result, hls::stream<pkt> &streaming_to, 
        hls::stream<pkt> &streaming_from){
    int i;
    for(i = 0; i < TOP_APPEND*STAGE_COUNT; i++){
#pragma HLS pipeline II=1        
        pkt temp; 
        temp.data = result[i + GRID_COLS/WIDTH_FACTOR*PART_ROWS].range(511, 0);
        streaming_to.write(temp);  
    }
    for(i = 0; i < BOTTOM_APPEND*STAGE_COUNT; i++){
#pragma HLS pipeline II=1
        pkt temp2 = streaming_from.read();          
        result[i + GRID_COLS/PARA_FACTOR*PART_ROWS + (TOP_APPEND-BOTTOM_APPEND)*STAGE_COUNT].range(511, 0) = temp2.data;
    }
}

static void exchange_stream(INTERFACE_WIDTH *result, 
        hls::stream<pkt> &streaming_to_up, hls::stream<pkt> &streaming_from_up, 
        hls::stream<pkt> &streaming_to_down, hls::stream<pkt> &streaming_from_down){
    exchange_with_up(result, streaming_to_up, streaming_from_up);
    exchange_with_down(result, streaming_to_down, streaming_from_down);
}
'''

down_exchange = '''
static void exchange_stream(INTERFACE_WIDTH *result, hls::stream<pkt> &streaming_to, hls::stream<pkt> &streaming_from){
    int i;
    for(i = 0; i < TOP_APPEND*STAGE_COUNT; i++){
#pragma HLS pipeline II=1
        pkt temp2 = streaming_from.read();          
        result[i].range(511, 0) = temp2.data;
    }
    for(i = 0; i < BOTTOM_APPEND*STAGE_COUNT; i++){
#pragma HLS pipeline II=1        
        pkt temp; 
        temp.data = result[i + TOP_APPEND*STAGE_COUNT].range(511, 0);
        streaming_to.write(temp);
    }
}
'''