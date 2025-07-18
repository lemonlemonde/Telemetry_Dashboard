#ifndef UTILS_H
#define UTILS_H

#include <string>
#include <boost/date_time/posix_time/posix_time.hpp>

float get_randf_in_range(float lower, float upper);

std::string get_iso8601_timestamp();

#endif
