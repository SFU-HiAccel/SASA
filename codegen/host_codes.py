includes = '''
// This extension file is required for stream APIs
#include "CL/cl_ext_xilinx.h"
// This file is required for OpenCL C++ wrapper APIs
#include "xcl2.hpp"
'''

HBM_def = '''
// HBM Pseudo-channel(PC) requirements
#define MAX_HBM_PC_COUNT 32
#define PC_NAME(n) n | XCL_MEM_TOPOLOGY
const int pc[MAX_HBM_PC_COUNT] = {
    PC_NAME(0),  PC_NAME(1),  PC_NAME(2),  PC_NAME(3),  PC_NAME(4),  PC_NAME(5),  PC_NAME(6),  PC_NAME(7),
    PC_NAME(8),  PC_NAME(9),  PC_NAME(10), PC_NAME(11), PC_NAME(12), PC_NAME(13), PC_NAME(14), PC_NAME(15),
    PC_NAME(16), PC_NAME(17), PC_NAME(18), PC_NAME(19), PC_NAME(20), PC_NAME(21), PC_NAME(22), PC_NAME(23),
    PC_NAME(24), PC_NAME(25), PC_NAME(26), PC_NAME(27), PC_NAME(28), PC_NAME(29), PC_NAME(30), PC_NAME(31)};
'''

reset_function = '''
////////////////////RESET FUNCTION//////////////////////////////////
int fill_buffer(float* buffer, std::ifstream &data_input, size_t offset, size_t length) {
    data_input.seekg(std::ios::beg);

    float temp;
    for(size_t i = 0; i < offset; i++){
        data_input >> temp;
    }
    for(size_t i = 0; i < length; i++){
        data_input >> buffer[i];
    }

    return 0;
}

int fill_buffer(std::vector<float> &buffer, std::ifstream &data_input, size_t offset, size_t length) {
    data_input.seekg(std::ios::beg);

    float temp;
    for(size_t i = 0; i < offset; i++){
        data_input >> temp;
    }
    for(size_t i = 0; i < length; i++){
        data_input >> buffer[i];
    }

    return 0;
}

'''

verify_function = '''
///////////////////VERIFY FUNCTION///////////////////////////////////
bool verify(std::vector<std::vector<float, aligned_allocator<float> > >& results) {
    bool match = true;
    std::ofstream out("output.data");
    std::ofstream report("report.txt");
    out.precision(18);
    report.precision(18);
    out << std::fixed;
    report << std::fixed;

    std::vector<float> check_val(GRID_COLS*GRID_ROWS);
    const std::string check_path("../data/check.data");
    std::ifstream check_file(check_path);
    fill_buffer(check_val, check_file, 0, GRID_COLS * GRID_ROWS);
    check_file.close();
    
    for(int i = 0; i < KERNEL_COUNT; i++){
        for(int j = 0; j < GRID_COLS * PART_ROWS; j++){
            out << results[i][j + (TOP_APPEND+OVERLAP_TOP_OVERHEAD)*WIDTH_FACTOR] << std::endl;
        
            if(fabs(results[i][j + (TOP_APPEND+OVERLAP_TOP_OVERHEAD)*WIDTH_FACTOR] 
                        - check_val[i * GRID_COLS * PART_ROWS + j]) > 1e-10){
                        
                report << "Unmatch in position" << i << " : " << j / GRID_COLS << " : " << j % GRID_COLS 
                    << "where " << results[i][j + (TOP_APPEND+OVERLAP_TOP_OVERHEAD)*WIDTH_FACTOR] << " != " 
                    << check_val[i * GRID_COLS * PART_ROWS + j] << std::endl;
                
                match = false;            
            }
        }
    }
    
    std::cout << "TEST " << (match ? "PASSED" : "FAILED") << std::endl;
    return match;
}
'''

unikernel_init_opencl = '''
    if (argc != 2) {
        std::cout << "Usage: " << argv[0] << " <XCLBIN File>" << std::endl;
        return EXIT_FAILURE;
    }

    // OpenCL Host Code Begins.
    cl_int err;

    // OpenCL objects
    cl::Device device;
    cl::Context context;
    cl::CommandQueue q;
    cl::Program program;
    std::vector<cl::Kernel> kernels;

    auto binaryFile = argv[1];

    // get_xil_devices() is a utility API which will find the xilinx
    // platforms and will return list of devices connected to Xilinx platform
    auto devices = xcl::get_xil_devices();

    // read_binary_file() is a utility API which will load the binaryFile
    // and will return the pointer to file buffer.
    auto fileBuf = xcl::read_binary_file(binaryFile);
    cl::Program::Binaries bins{{fileBuf.data(), fileBuf.size()}};
    bool valid_device = false;
    for (unsigned int i = 0; i < devices.size(); i++) {
        device = devices[i];
        // Creating Context and Command Queue for selected Device
        OCL_CHECK(err, context = cl::Context(device, NULL, NULL, NULL, &err));
        OCL_CHECK(err, q = cl::CommandQueue(context, device,
                                            CL_QUEUE_PROFILING_ENABLE | CL_QUEUE_OUT_OF_ORDER_EXEC_MODE_ENABLE, &err));
        std::cout << "Trying to program device[" << i << "]: " << device.getInfo<CL_DEVICE_NAME>() << std::endl;
        cl::Program program(context, {device}, bins, NULL, &err);
        if (err != CL_SUCCESS) {
            std::cout << "Failed to program device[" << i << "] with xclbin file!\\n";
        } else {
            std::cout << "Device[" << i << "]: program successful!\\n";
            // Creating Kernel
            char kernel_name[50];
            for(int k = 0; k < KERNEL_COUNT; k++){
                sprintf(kernel_name, "unikernel:{unikernel_%d}", k+1);
                OCL_CHECK(err, kernels.emplace_back(program, kernel_name, &err));
            }
            valid_device = true;
            break; // we break because we found a valid device
        }
    }
    if (!valid_device) {
        std::cout << "Failed to program any device found, exit!\\n";
        exit(EXIT_FAILURE);
    }
'''

streaming_kernel_init_opencl = '''
    if (argc != 2) {
        std::cout << "Usage: " << argv[0] << " <XCLBIN File>" << std::endl;
        return EXIT_FAILURE;
    }

    // OpenCL Host Code Begins.
    cl_int err;

    // OpenCL objects
    cl::Device device;
    cl::Context context;
    cl::CommandQueue q;
    cl::Program program;
    std::vector<cl::Kernel> kernels;

    auto binaryFile = argv[1];

    // get_xil_devices() is a utility API which will find the xilinx
    // platforms and will return list of devices connected to Xilinx platform
    auto devices = xcl::get_xil_devices();

    // read_binary_file() is a utility API which will load the binaryFile
    // and will return the pointer to file buffer.
    auto fileBuf = xcl::read_binary_file(binaryFile);
    cl::Program::Binaries bins{{fileBuf.data(), fileBuf.size()}};
    bool valid_device = false;
    for (unsigned int i = 0; i < devices.size(); i++) {
        device = devices[i];
        // Creating Context and Command Queue for selected Device
        OCL_CHECK(err, context = cl::Context(device, NULL, NULL, NULL, &err));
        OCL_CHECK(err, q = cl::CommandQueue(context, device,
                                            CL_QUEUE_PROFILING_ENABLE | CL_QUEUE_OUT_OF_ORDER_EXEC_MODE_ENABLE, &err));
        std::cout << "Trying to program device[" << i << "]: " << device.getInfo<CL_DEVICE_NAME>() << std::endl;
        cl::Program program(context, {device}, bins, NULL, &err);
        if (err != CL_SUCCESS) {
            std::cout << "Failed to program device[" << i << "] with xclbin file!\\n";
        } else {
            std::cout << "Device[" << i << "]: program successful!\\n";
            // Creating Kernel
            char kernel_name[50];
            for(int k = 0; k < KERNEL_COUNT; k++){
                if(k==0){
                    sprintf(kernel_name, "upkernel");
                }else if(k==KERNEL_COUNT-1){
                    sprintf(kernel_name, "downkernel");
                }else{
                    sprintf(kernel_name, "midkernel:{midkernel_%d}", k+1);
                }
                OCL_CHECK(err, kernels.emplace_back(program, kernel_name, &err));
            }
            valid_device = true;
            break; // we break because we found a valid device
        }
    }
    if (!valid_device) {
        std::cout << "Failed to program any device found, exit!\\n";
        exit(EXIT_FAILURE);
    }
'''