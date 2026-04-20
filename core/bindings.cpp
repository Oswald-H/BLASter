#include <nanobind/nanobind.h>
#include <nanobind/ndarray.h>
#include <omp.h>

#include <algorithm>
#include <cstring>
#include <string>
#include <vector>

#include "types.hpp"

void lll_reduce(const int N, FT *R, ZZ *U, const FT delta);
void deeplll_reduce(const int N, FT *R, ZZ *U, const FT delta, const int depth);
void bkz_reduce(const int N, FT *R, ZZ *U, const FT delta, const int beta);

void eigen_init(int num_cores);
void eigen_matmul(const ZZ *a, const ZZ *b, ZZ *c, int n, int m, int k);
void eigen_left_matmul(const ZZ *a, ZZ *b, int n, int m, int stride_a, int stride_b);
void eigen_right_matmul(ZZ *a, const ZZ *b, int n, int m);
void eigen_right_matmul(ZZ *a, const ZZ *b, int n, int m, int stride_a);

namespace nb = nanobind;

namespace
{

    template <typename Scalar, typename... Constraints>
    using Mat = nb::ndarray<Scalar, nb::numpy, nb::ndim<2>, nb::device::cpu, Constraints...>;

    // Matrix aliases:
    // C means const, D means dense C-contiguous;
    // aliases without D accept row-strided views whose last axis is contiguous.
    using FTMat = Mat<FT>;
    using CFTMat = Mat<const FT>;
    using DZZMat = Mat<ZZ, nb::c_contig>;
    using CDZZMat = Mat<const ZZ, nb::c_contig>;
    using ZZMat = Mat<ZZ>;
    using CZZMat = Mat<const ZZ>;

    int debug_size_reduction;

    template <typename Matrix>
    void check_row_major(const Matrix &matrix, const char *name)
    {
        if (matrix.stride(1) != 1)
        {
            const std::string message = std::string(name) + " must have a contiguous last axis";
            throw nb::value_error(message.c_str());
        }
    }

    template <typename Reducer>
    void block_reduce(const FTMat &R, const ZZMat &B_red, const ZZMat &U, int offset, int block_size, Reducer reducer)
    {
        check_row_major(R, "R");
        check_row_major(B_red, "B_red");
        check_row_major(U, "U");

        const int n = static_cast<int>(R.shape(0));
        const int num_blocks = (n - offset + block_size - 1) / block_size;
        const int stride_r = static_cast<int>(R.stride(0));
        const int stride_u = static_cast<int>(U.stride(0));
        const int stride_b = static_cast<int>(B_red.stride(0));
        const int u_rows = static_cast<int>(U.shape(0));
        const int b_rows = static_cast<int>(B_red.shape(0));
        const int batch_size = std::max(1, omp_get_max_threads());
        const size_t block_area = static_cast<size_t>(block_size) * static_cast<size_t>(block_size);

        for (int batch_start = 0; batch_start < num_blocks; batch_start += batch_size)
        {
            const int batch_blocks = std::min(batch_size, num_blocks - batch_start);
            std::vector<FT> R_blocks(static_cast<size_t>(batch_blocks) * block_area);
            std::vector<ZZ> U_blocks(static_cast<size_t>(batch_blocks) * block_area);

            {
                nb::gil_scoped_release release;

#pragma omp parallel for schedule(static)

                for (int local_block = 0; local_block < batch_blocks; ++local_block)
                {
                    const int block_id = batch_start + local_block;
                    const int start = offset + block_size * block_id;
                    const int width = std::min(n - start, block_size);
                    FT *block_r = R_blocks.data() + static_cast<size_t>(local_block) * block_area;
                    ZZ *block_u = U_blocks.data() + static_cast<size_t>(local_block) * block_area;

                    for (int row = 0; row < width; ++row)
                    {
                        std::memcpy(block_r + static_cast<size_t>(row) * static_cast<size_t>(width),
                                    R.data() + static_cast<size_t>(start + row) * static_cast<size_t>(stride_r) + start,
                                    static_cast<size_t>(width) * sizeof(FT));
                    }

                    reducer(width, block_r, block_u);

                    if (debug_size_reduction == 0) continue;

                    for (int row = 0; row < width; ++row)
                    {
                        std::memcpy(R.data() + static_cast<size_t>(start + row) * static_cast<size_t>(stride_r) + start,
                                    block_r + static_cast<size_t>(row) * static_cast<size_t>(width),
                                    static_cast<size_t>(width) * sizeof(FT));
                    }
                }

                for (int local_block = 0; local_block < batch_blocks; ++local_block)
                {
                    const int block_id = batch_start + local_block;
                    const int start = offset + block_size * block_id;
                    const int width = std::min(n - start, block_size);
                    const ZZ *block_u = U_blocks.data() + static_cast<size_t>(local_block) * block_area;

                    eigen_right_matmul(U.data() + start, block_u, u_rows, width, stride_u);
                    eigen_right_matmul(B_red.data() + start, block_u, b_rows, width, stride_b);
                }
            }

            if (PyErr_CheckSignals() != 0) throw nb::python_error();
        }
    }

}  // namespace

NB_MODULE(_core, m)
{
    m.def("set_debug_flag", [](int flag) { debug_size_reduction = flag; });

    m.def("set_num_cores",
          [](int num_cores)
          {
              omp_set_num_threads(num_cores);
              eigen_init(num_cores);
          });

    m.def(
        "block_lll",
        [](const FTMat &R, const ZZMat &B_red, const ZZMat &U, FT delta, int offset, int block_size)
        {
            block_reduce(R, B_red, U, offset, block_size,
                         [delta](int n, FT *block_r, ZZ *block_u) { lll_reduce(n, block_r, block_u, delta); });
        },
        nb::arg("R").noconvert(), nb::arg("B_red").noconvert(), nb::arg("U").noconvert(), nb::arg("delta"),
        nb::arg("offset"), nb::arg("block_size"));

    m.def(
        "block_deep_lll",
        [](int depth, const FTMat &R, const ZZMat &B_red, const ZZMat &U, FT delta, int offset, int block_size)
        {
            block_reduce(R, B_red, U, offset, block_size, [delta, depth](int n, FT *block_r, ZZ *block_u)
                         { deeplll_reduce(n, block_r, block_u, delta, depth); });
        },
        nb::arg("depth"), nb::arg("R").noconvert(), nb::arg("B_red").noconvert(), nb::arg("U").noconvert(),
        nb::arg("delta"), nb::arg("offset"), nb::arg("block_size"));

    m.def(
        "block_bkz",
        [](int beta, const FTMat &R, const ZZMat &B_red, const ZZMat &U, FT delta, int offset, int block_size)
        {
            block_reduce(R, B_red, U, offset, block_size, [delta, beta](int n, FT *block_r, ZZ *block_u)
                         { bkz_reduce(n, block_r, block_u, delta, beta); });
        },
        nb::arg("beta"), nb::arg("R").noconvert(), nb::arg("B_red").noconvert(), nb::arg("U").noconvert(),
        nb::arg("delta"), nb::arg("offset"), nb::arg("block_size"));

    m.def(
        "FT_matmul",
        [](const CFTMat &A, const CFTMat &B)
        {
            if (A.shape(1) != B.shape(0)) throw nb::value_error("A.shape[1] must match B.shape[0]");

            static nb::object numpy_matmul = nb::module_::import_("numpy").attr("matmul");
            return numpy_matmul(A, B);
        },
        nb::arg("A").noconvert(), nb::arg("B").noconvert());

    m.def(
        "ZZ_matmul",
        [](const CDZZMat &A, const CDZZMat &B) -> DZZMat
        {
            if (A.shape(1) != B.shape(0)) throw nb::value_error("A.shape[1] must match B.shape[0]");

            const int n = static_cast<int>(A.shape(0));
            const int m = static_cast<int>(A.shape(1));
            const int k = static_cast<int>(B.shape(1));

            auto *data = new ZZ[static_cast<size_t>(n) * static_cast<size_t>(k)];

            nb::capsule owner(data, [](void *ptr) noexcept { delete[] static_cast<ZZ *>(ptr); });
            DZZMat C(data, {static_cast<size_t>(n), static_cast<size_t>(k)}, owner);

            {
                nb::gil_scoped_release release;
                eigen_matmul(A.data(), B.data(), C.data(), n, m, k);
            }

            return C;
        },
        nb::arg("A").noconvert(), nb::arg("B").noconvert());

    m.def(
        "ZZ_left_matmul_strided",
        [](const CZZMat &A, const ZZMat &B)
        {
            check_row_major(A, "A");
            check_row_major(B, "B");

            if (A.shape(0) != A.shape(1)) throw nb::value_error("A must be square");
            if (A.shape(0) != B.shape(0)) throw nb::value_error("A.shape[0] must match B.shape[0]");

            const int n = static_cast<int>(B.shape(0));
            const int m = static_cast<int>(B.shape(1));

            {
                nb::gil_scoped_release release;
                eigen_left_matmul(A.data(), B.data(), n, m, static_cast<int>(A.stride(0)),
                                  static_cast<int>(B.stride(0)));
            }
        },
        nb::arg("A").noconvert(), nb::arg("B").noconvert());

    m.def(
        "ZZ_right_matmul",
        [](const DZZMat &A, const CDZZMat &B)
        {
            if (B.shape(0) != A.shape(1) || B.shape(1) != A.shape(1))
                throw nb::value_error("B must be square with size A.shape[1]");

            const int n = static_cast<int>(A.shape(0));
            const int m = static_cast<int>(A.shape(1));

            {
                nb::gil_scoped_release release;
                eigen_right_matmul(A.data(), B.data(), n, m);
            }
        },
        nb::arg("A").noconvert(), nb::arg("B").noconvert());

    m.def(
        "ZZ_right_matmul_strided",
        [](const ZZMat &A, const CDZZMat &B)
        {
            check_row_major(A, "A");

            if (B.shape(0) != A.shape(1) || B.shape(1) != A.shape(1))
                throw nb::value_error("B must be square with size A.shape[1]");

            const int n = static_cast<int>(A.shape(0));
            const int m = static_cast<int>(A.shape(1));

            {
                nb::gil_scoped_release release;
                eigen_right_matmul(A.data(), B.data(), n, m, static_cast<int>(A.stride(0)));
            }
        },
        nb::arg("A").noconvert(), nb::arg("B").noconvert());
}
