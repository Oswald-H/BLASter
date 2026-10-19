/*
MIT License

Copyright (c) 2024 Marc Stevens

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
*/

#ifndef ENUMLIB_ENUMERATION_HPP
#define ENUMLIB_ENUMERATION_HPP

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>

#include "types.hpp"

#define NOCOUNTS 1

template <int N>
struct lattice_enum_t
{
    typedef std::array<FT, N> fltrow_t;
    typedef std::array<ZZ, N> introw_t;

    /* inputs */
    // mu^T corresponds to R (B=Q*R) with multiplicative corrections: muT[i][j] = R[i][j] / R[i][i]
    // mu^T is the transposed mu in fplll (see also: An LLL Algorithm with Quadratic Complexity, Nguyen, Stehle, 2009.)
    FT muT[N][N];
    // risq[i] is ||bi*||^2, or R[i][i]*R[i][i]
    fltrow_t risq;
    // the *relative* pruning bounds for the squared norm within the projected sublattices.
    fltrow_t pr;

    /* internals */
    FT A;  // overall enumeration bound
    fltrow_t AA;  // enumeration pruning bounds
    introw_t x, Dx, D2x;
    fltrow_t sol;  // to pass to fplll
    fltrow_t c;
    introw_t r;
    std::array<FT, N + 1> l;
    std::array<std::uint64_t, N + 1> counts;

    FT sigT[N][N];

    lattice_enum_t() : muT(), risq(), pr() {}

    inline void update_AA()
    {
        // ensure that the pruning bounds are non-increasing from a basis perspective.
        for (int k = 0; k < N; ++k)
        {
            AA[k] = A * pr[k];
        }
    }

    // compile time parameters for enumerate_recur (without ANY runtime overhead)
    // allows specialization for certain specific cases, e.g., i=0
    template <int i>
    struct i_tag
    {
    };

    template <int i>
    inline void enumerate_recur(i_tag<i>)
    {
        if (r[i] > r[i - 1]) r[i - 1] = r[i];
        FT ci = sigT[i][i];
        FT yi = round(ci);
        ZZ xi = static_cast<ZZ>(yi);
        yi = ci - yi;
        FT li = l[i + 1] + (yi * yi * risq[i]);
#ifndef NOCOUNTS
        ++counts[i];
#endif

        if (li > AA[i]) return;

        Dx[i] = D2x[i] = (((int)(yi >= 0) & 1) << 1) - 1;
        c[i] = ci;
        x[i] = xi;
        l[i] = li;

        for (int j = r[i - 1]; j > i - 1; --j) sigT[i - 1][j - 1] = sigT[i - 1][j] - x[j] * muT[i - 1][j];

        while (true)
        {
            enumerate_recur(i_tag<i - 1>());

            if (l[i + 1] == 0.0)
            {
                ++x[i];
            }
            else
            {
                x[i] += Dx[i];
                D2x[i] = -D2x[i];
                Dx[i] = D2x[i] - Dx[i];
            }

            r[i - 1] = i;
            FT yi2 = c[i] - x[i];
            FT li2 = l[i + 1] + (yi2 * yi2 * risq[i]);
            if (li2 > AA[i]) return;
            l[i] = li2;
            sigT[i - 1][i - 1] = sigT[i - 1][i] - x[i] * muT[i - 1][i];
        }
    }

    inline void enumerate_recur(i_tag<0>)
    {
        static constexpr int i = 0;
        FT ci = sigT[i][i];
        FT yi = round(ci);
        ZZ xi = static_cast<ZZ>(yi);
        yi = ci - yi;
        FT li = l[i + 1] + (yi * yi * risq[i]);
#ifndef NOCOUNTS
        ++counts[i];
#endif

        if (li > AA[i]) return;

        Dx[i] = D2x[i] = (((int)(yi >= 0) & 1) << 1) - 1;
        c[i] = ci;
        x[i] = xi;
        l[i] = li;

        while (true)
        {
            enumerate_recur(i_tag<i - 1>());

            if (l[i + 1] == 0.0)
            {
                ++x[i];
            }
            else
            {
                x[i] += Dx[i];
                D2x[i] = -D2x[i];
                Dx[i] = D2x[i] - Dx[i];
            }

            FT yi2 = c[i] - x[i];
            FT li2 = l[i + 1] + (yi2 * yi2 * risq[i]);
            if (li2 > AA[i]) return;
            l[i] = li2;
        }
    }

    inline void enumerate_recur(i_tag<-1>)
    {
        if (l[0] > A || l[0] == 0.0) return;

        for (int j = 0; j < N; ++j) sol[j] = x[j];

        A = l[0];
        update_AA();
    }

    inline void enumerate_recursive()
    {
        update_AA();

        std::fill(l.begin(), l.end(), 0.0);
        std::fill(x.begin(), x.end(), 0);
        std::fill(Dx.begin(), Dx.end(), 0);
        std::fill(D2x.begin(), D2x.end(), -1);
        std::fill(c.begin(), c.end(), 0.0);

        std::fill(r.begin(), r.end(), N - 1);
        std::fill_n(&sigT[0][0], N * N, 0.0);

        std::fill(sol.begin(), sol.end(), 0);
        std::fill(counts.begin(), counts.end(), 0);

        enumerate_recur(i_tag<N - 1>());
    }
};

#endif  // ENUMLIB_ENUMERATION_HPP
